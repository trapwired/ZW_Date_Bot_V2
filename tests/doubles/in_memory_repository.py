"""In-memory Repository backend for tests.

A dict-backed hierarchical document store plus a Repository implementation on
top of it, so DataAccess and everything above runs for real under test with no
external services. Its seam semantics are pinned against PostgresRepository by
the contract suite (tests/contract) - if the two drift, contract tests fail.

Only the store surface the repository actually exercises is implemented;
anything else raises so gaps surface loudly instead of silently.
"""
from datetime import datetime

import pandas as pd

from data.Repository import Repository
from data.Tables import Tables, EVENT_TABLES, EVENT_ATTENDANCE_TABLES, GLOBAL_TABLES, TEAM_SCOPED_TABLES
from data.TenantContext import current_team_id, team_context

from Enums.Table import Table
from Enums.Role import Role
from Enums.Event import Event

from domain.Season import get_current_season_dates
from domain.entities.DatabaseEntity import DatabaseEntity
from domain.entities.Game import Game
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training
from domain.entities.Attendance import Attendance
from domain.entities.PlayerMetric import PlayerMetric
from domain.entities.TempData import TempData
from domain.entities.Settings import Settings

from Utils.CustomExceptions import ObjectNotFoundException, MoreThanOneObjectFoundException, \
    NoTempDataFoundException, TooManyObjectsFoundException
from Utils import DateTimeUtils


def _strip_tz(value):
    # Stored event timestamps are tz-aware (Europe/Zurich); query bounds are naive
    # datetimes. Normalise both to naive for ordering comparisons so instants compare
    # regardless of tz representation (Postgres timestamptz behaves the same way).
    if isinstance(value, pd.Timestamp):
        return value.tz_localize(None) if value.tzinfo is not None else value
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


class _FieldFilter:
    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value

    def matches(self, data: dict) -> bool:
        actual = data.get(self.field)
        if self.op == "==":
            return actual == self.value
        if self.op == "in":
            return actual in self.value
        if self.op in (">", "<", ">=", "<="):
            if actual is None:
                return False
            a, b = _strip_tz(actual), _strip_tz(self.value)
            if self.op == ">":
                return a > b
            if self.op == "<":
                return a < b
            if self.op == ">=":
                return a >= b
            return a <= b
        raise NotImplementedError(f"_FieldFilter op not supported: {self.op}")


class _Row:
    """A query/read result: the `.id` + `.to_dict()` row contract of the seam."""

    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _DocumentRef:
    def __init__(self, collection: "_Collection", doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self):
        return _Row(self.id, self._collection.store.get(self.id))

    def set(self, data: dict):
        self._collection.store[self.id] = dict(data)

    def update(self, data: dict):
        # Merges top-level keys, it does not replace the doc.
        existing = self._collection.store.setdefault(self.id, {})
        existing.update(data)

    def delete(self):
        self._collection.store.pop(self.id, None)

    def collection(self, name: str) -> "_Collection":
        # Subcollections key the shared storage by path, mirroring the teams/{id}/<name>
        # hierarchy. Works even for a doc that doesn't exist yet.
        return _Collection(self._collection._store, f"{self._collection.name}/{self.id}/{name}")


class _Query:
    def __init__(self, collection: "_Collection", filters):
        self._collection = collection
        self._filters = filters

    def where(self, filter):  # noqa: A002 - mirrors the query-builder kwarg name
        return _Query(self._collection, self._filters + [filter])

    def get(self):
        return [_Row(doc_id, data)
                for doc_id, data in list(self._collection.store.items())
                if all(f.matches(data) for f in self._filters)]

    def stream(self):
        return iter(self.get())


class _Collection:
    def __init__(self, store: "_MemoryStore", name: str):
        self._store = store
        self.name = name
        self.store = store.storage.setdefault(name, {})

    def document(self, doc_id: str = None):
        if doc_id is None:
            doc_id = self._store.next_id()
        return _DocumentRef(self, doc_id)

    def where(self, filter):  # noqa: A002 - mirrors the query-builder kwarg name
        return _Query(self, [filter])

    def add(self, data: dict) -> _DocumentRef:
        doc_id = self._store.next_id()
        self.store[doc_id] = dict(data)
        return _DocumentRef(self, doc_id)

    def stream(self):
        return iter(self.get())

    def get(self):
        return [_Row(doc_id, data) for doc_id, data in list(self.store.items())]

    def limit(self, count: int):
        return _LimitedCollection(self, count)


class _LimitedCollection:
    def __init__(self, collection: _Collection, count: int):
        self._collection = collection
        self._count = count

    def get(self):
        return self._collection.get()[:self._count]


class _MemoryStore:
    def __init__(self):
        self.storage = {}
        self._counter = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"doc{self._counter}"

    def collection(self, name: str) -> _Collection:
        return _Collection(self, name)


class InMemoryRepository(Repository):
    # The settings table holds a single configuration document under a fixed id, so it can be
    # read/written deterministically without a query (no "more than one" ambiguity).
    SETTINGS_DOC_ID = 'config'

    def __init__(self, tables: Tables):
        self.tables = tables
        self.db = _MemoryStore()

    def _collection(self, table: Table):
        """THE tenancy seam: every collection access resolves through here. Team-scoped
        tables land under teams/{current team}/<name> and fail closed (raise) when no
        team is resolved; global tables resolve flat."""
        name = self.tables.get(table)
        if table in GLOBAL_TABLES:
            return self.db.collection(name)
        return (self.db.collection(self.tables.get(Table.TEAMS_TABLE))
                .document(current_team_id())
                .collection(name))

    def _raise_exception_if_document_not_exists(self, table: Table, document_ref: str):
        doc = self._collection(table).document(document_ref)
        res = doc.get().to_dict()
        if res is None:
            raise ObjectNotFoundException(self.tables.get(table), document_ref)

    #######
    # GET #
    #######

    def get_document(self, doc_id: str, table: Table):
        self._raise_exception_if_document_not_exists(table, doc_id)
        return self._collection(table).document(doc_id).get()

    def get_user(self, telegram_id_or_doc_id: int | str) -> TelegramUser | None:
        if isinstance(telegram_id_or_doc_id, str):
            res = self.get_document(telegram_id_or_doc_id, Table.USERS_TABLE)
            return TelegramUser.from_dict(res.id, res.to_dict())

        res = self._collection(Table.USERS_TABLE).where(
            _FieldFilter("telegramId", "==", telegram_id_or_doc_id)).get()
        if len(res) == 0:
            raise ObjectNotFoundException(self.tables.get(Table.USERS_TABLE), telegram_id_or_doc_id)
        if len(res) == 1:
            return TelegramUser.from_dict(res[0].id, res[0].to_dict())
        raise MoreThanOneObjectFoundException

    def get_user_state(self, user: TelegramUser) -> UsersToState | None:
        user_id = user.doc_id
        res = self._collection(Table.USERS_TO_STATE_TABLE).where(
            _FieldFilter("userId", "==", user_id)).get()
        if len(res) == 1:
            return UsersToState.from_dict(res[0].id, res[0].to_dict())
        if len(res) > 1:
            # Duplicate state docs for one user are data corruption, not a not-found; fail
            # loudly so it isn't silently masked as a missing user.
            raise MoreThanOneObjectFoundException()
        raise ObjectNotFoundException(self.tables.get(Table.USERS_TO_STATE_TABLE), user_id)

    def get_game(self, doc_id: str) -> Game | None:
        res = self.get_document(doc_id, Table.GAMES_TABLE)
        return Game.from_dict(res.id, res.to_dict())

    def get_training(self, doc_id: str) -> Training | None:
        res = self.get_document(doc_id, Table.TRAININGS_TABLE)
        return Training.from_dict(res.id, res.to_dict())

    def get_timekeeping(self, doc_id: str) -> TimekeepingEvent | None:
        res = self.get_document(doc_id, Table.TIMEKEEPING_TABLE)
        return TimekeepingEvent.from_dict(res.id, res.to_dict())

    def get_team(self, doc_id: str) -> Team:
        res = self.get_document(doc_id, Table.TEAMS_TABLE)
        return Team.from_dict(res.id, res.to_dict())

    def get_all_teams(self) -> list[Team]:
        entries = self._collection(Table.TEAMS_TABLE).get()
        return [Team.from_dict(entry.id, entry.to_dict()) for entry in entries]

    def get_player_metric(self, user: TelegramUser):
        season_start, season_end = get_current_season_dates()
        entries = (self._collection(Table.PLAYER_METRIC)
                   .where(_FieldFilter("userId", "==", user.doc_id))
                   .where(_FieldFilter("insertTimestamp", ">", season_start))
                   .where(_FieldFilter("insertTimestamp", "<", season_end))).get()
        if len(entries) == 1:
            return PlayerMetric.from_dict(entries[0].id, entries[0].to_dict())
        if len(entries) > 1:
            # A player should only ever have one metric per season; if a race created duplicates,
            # self-heal by collapsing to a single record (the query has no ordering, so which one
            # survives is arbitrary) so later reads aren't ambiguous.
            for entry in entries[1:]:
                self._collection(Table.PLAYER_METRIC).document(entry.id).delete()
            return PlayerMetric.from_dict(entries[0].id, entries[0].to_dict())
        new_player_metric = PlayerMetric(user.doc_id, 0, 0, 0, DateTimeUtils.get_local_now())
        doc_id = self.add(new_player_metric, Table.PLAYER_METRIC)
        return new_player_metric.add_document_id(doc_id)

    def get_temp_data(self, user_doc_id: str) -> TempData:
        result_list = (self._collection(Table.TEMP_DATA_TABLE)
                       .where(_FieldFilter("userDocId", "==", user_doc_id))).get()
        if len(result_list) == 0:
            raise NoTempDataFoundException()
        if len(result_list) > 1:
            raise TooManyObjectsFoundException()
        temp_data = result_list[0]
        return TempData.from_dict(temp_data.id, temp_data.to_dict())

    def get_settings(self) -> Settings | None:
        doc = self._collection(Table.SETTINGS_TABLE).document(self.SETTINGS_DOC_ID).get()
        if not doc.exists:
            return None
        return Settings.from_dict(doc.id, doc.to_dict())

    def set_settings(self, settings: Settings):
        # Upsert: creates the single settings document on first save, overwrites it afterwards.
        self._collection(Table.SETTINGS_TABLE).document(self.SETTINGS_DOC_ID).set(settings.to_dict())

    def get_future_events(self, table: Table) -> list:
        return self._collection(table).where(
            _FieldFilter("timestamp", ">", datetime.now())).get()

    def get_attendance_list(self, doc_id: str, table: Table):
        return self._collection(table).where(_FieldFilter("eventId", "==", doc_id)).get()

    def get_attendance(self, user: TelegramUser, event_doc_id: str, table: Table):
        result = (self._collection(table)
                  .where(_FieldFilter("userId", "==", user.doc_id))
                  .where(_FieldFilter("eventId", "==", event_doc_id))).get()
        if len(result) == 0:
            raise ObjectNotFoundException(self.tables.get(table), user.doc_id)
        if len(result) > 1:
            raise MoreThanOneObjectFoundException()
        attendance = result[0]
        return Attendance.from_dict(attendance.id, attendance.to_dict())

    def get_all_user_event_attendance(self, user: TelegramUser, event_type: Event):
        table = self._get_event_attendance_table(event_type)
        return self._collection(table).where(_FieldFilter("userId", "==", user.doc_id)).get()

    def get_all_event_attendances(self, event_type: Event, relevant_doc_ids: list[str]):
        if len(relevant_doc_ids) == 0:
            return []
        table = self._get_event_attendance_table(event_type)
        return self._collection(table).where(
            _FieldFilter("eventId", "in", relevant_doc_ids)).get()

    def get_all_relevant_event_ids(self, event_type: Event):
        table = self._get_event_table(event_type)
        season_start, _ = get_current_season_dates()
        entries = (self._collection(table)
                   .where(_FieldFilter("timestamp", ">", season_start))
                   .where(_FieldFilter("timestamp", "<", DateTimeUtils.get_local_now()))).get()
        return [row.id for row in entries]

    def get_all_player_metrics(self):
        season_start, season_end = get_current_season_dates()
        return (self._collection(Table.PLAYER_METRIC)
                .where(_FieldFilter("insertTimestamp", ">", season_start))
                .where(_FieldFilter("insertTimestamp", "<", season_end))).get()

    def get_users_to_state_by_role(self, role: Role):
        # users_to_state is a global identity table, but role queries are roster views -
        # inherently team-scoped, so they filter on the ambient team (and fail closed
        # without one) even though the collection itself is not partitioned.
        return (self._collection(Table.USERS_TO_STATE_TABLE)
                .where(_FieldFilter("role", "==", role))
                .where(_FieldFilter("teamId", "==", current_team_id()))).get()

    def get_admins_to_state(self):
        # Admin is the orthogonal isAdmin flag, not a role - same team-scoped roster
        # view as get_users_to_state_by_role.
        return (self._collection(Table.USERS_TO_STATE_TABLE)
                .where(_FieldFilter("isAdmin", "==", True))
                .where(_FieldFilter("teamId", "==", current_team_id()))).get()

    def get_users_to_state_by_team(self, team_id: str):
        # Membership view over the global identity table, keyed explicitly (used by
        # team-lifecycle code that runs OUTSIDE the ambient tenant context).
        return self._collection(Table.USERS_TO_STATE_TABLE).where(
            _FieldFilter("teamId", "==", team_id)).get()

    def has_any_docs(self, table: Table) -> bool:
        return len(self._collection(table).limit(1).get()) > 0

    def delete_team(self, doc_id: str):
        # A rolled-back team must purge its team-scoped docs first (a fresh team holds at
        # most a settings doc or an abandoned wizard draft) or they orphan forever.
        with team_context(doc_id):
            for table in TEAM_SCOPED_TABLES:
                collection = self._collection(table)
                for doc in collection.get():
                    collection.document(doc.id).delete()
        self._collection(Table.TEAMS_TABLE).document(doc_id).delete()

    def get_all_active_players_to_state(self):
        # Roster view over the global identity table - team-filtered like
        # get_users_to_state_by_role above.
        return (self._collection(Table.USERS_TO_STATE_TABLE)
                .where(_FieldFilter("role", "==", Role.PLAYER))
                .where(_FieldFilter("teamId", "==", current_team_id()))).get()

    def get_event_attendance_doc_id(self, attendance: Attendance, table: Table):
        result = (self._collection(table)
                  .where(_FieldFilter("userId", "==", attendance.user_id))
                  .where(_FieldFilter("eventId", "==", attendance.event_id))).get()
        if len(result) == 0:
            return None
        if len(result) > 1:
            raise MoreThanOneObjectFoundException(attendance)
        return result[0].id

    ################
    # ADD / UPDATE #
    ################

    def add(self, new_object: DatabaseEntity, table: Table) -> str:
        return self._collection(table).add(new_object.to_dict()).id

    def update(self, db_object: DatabaseEntity, table: Table):
        self._raise_exception_if_document_not_exists(table, db_object.doc_id)
        self._collection(table).document(db_object.doc_id).update(db_object.to_dict())
        return db_object

    def update_user_state(self, user_to_state: UsersToState):
        self._raise_exception_if_document_not_exists(Table.USERS_TO_STATE_TABLE, user_to_state.doc_id)
        self._collection(Table.USERS_TO_STATE_TABLE).document(user_to_state.doc_id).update(
            {'state': int(user_to_state.state)})

    def update_user_state_via_user_id(self, user_to_state: UsersToState):
        res = self._collection(Table.USERS_TO_STATE_TABLE).where(
            _FieldFilter("userId", "==", user_to_state.user_id)).get()
        if len(res) == 1:
            updated_user_to_state = user_to_state.add_document_id(res[0].id)
            self.update_user_state(updated_user_to_state)
        elif len(res) > 1:
            # Duplicate state docs are data corruption, not a not-found; fail loudly.
            raise MoreThanOneObjectFoundException()
        else:
            raise ObjectNotFoundException(self.tables.get(Table.USERS_TO_STATE_TABLE), user_to_state.user_id)

    def update_user_via_telegram_id(self, user: TelegramUser):
        user_id = self.get_user(user.telegramId).doc_id
        user.add_document_id(user_id)  # sets doc_id in place (add_document_id mutates + returns self)
        return self.update(user, Table.USERS_TABLE)

    ##########
    # DELETE #
    ##########

    def delete_temp_data(self, temp_data: TempData):
        self._collection(Table.TEMP_DATA_TABLE).document(temp_data.doc_id).delete()

    def delete_game(self, doc_id: str):
        self._collection(Table.GAMES_TABLE).document(doc_id).delete()

    def delete_training(self, doc_id: str):
        self._collection(Table.TRAININGS_TABLE).document(doc_id).delete()

    def delete_timekeeping(self, doc_id: str):
        self._collection(Table.TIMEKEEPING_TABLE).document(doc_id).delete()

    def delete_event_attendances(self, event_type: Event, event_doc_id: str):
        table = self._get_event_attendance_table(event_type)
        rows = self._collection(table).where(_FieldFilter("eventId", "==", event_doc_id)).get()
        self._delete_documents(table, rows)

    def delete_all_player_metrics(self) -> int:
        return self._delete_documents(Table.PLAYER_METRIC, self._collection(Table.PLAYER_METRIC).get())

    def _delete_documents(self, table: Table, docs) -> int:
        deleted_count = 0
        for doc in docs:
            self._collection(table).document(doc.id).delete()
            deleted_count += 1
        return deleted_count

    ########
    # ELSE #
    ########

    def _get_event_attendance_table(self, event_type: Event) -> Table:
        return EVENT_ATTENDANCE_TABLES[event_type]

    def _get_event_table(self, event_type: Event) -> Table:
        return EVENT_TABLES[event_type]

    def reset_all_player_event_attendance(self, doc_id: str, table: Table):
        collection_reference = self._collection(table)
        attendance_rows = collection_reference.where(_FieldFilter("eventId", "==", doc_id)).get()
        for row in attendance_rows:
            collection_reference.document(row.id).update({"state": 0})
