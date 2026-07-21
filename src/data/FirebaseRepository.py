from datetime import datetime

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from data.Repository import Repository
from data.Tables import Tables, EVENT_TABLES, EVENT_ATTENDANCE_TABLES
from data.TenantContext import current_team_id, team_context

from Enums.Table import Table
from Enums.Role import Role
from Enums.Event import Event

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
from Utils import PathUtils
from Utils.ApiConfig import ApiConfig
from Utils import DateTimeUtils

# Tenancy classification (ADR 0001): identity and the team registry itself are global -
# team resolution needs the user record before a team is known; everything else lives
# under teams/{teamId}/<collection> and is unreachable without a tenant context.
GLOBAL_TABLES = {Table.USERS_TABLE, Table.USERS_TO_STATE_TABLE, Table.TEAMS_TABLE}
TEAM_SCOPED_TABLES = {
    Table.GAMES_TABLE, Table.TRAININGS_TABLE, Table.TIMEKEEPING_TABLE,
    Table.GAME_ATTENDANCE_TABLE, Table.TRAINING_ATTENDANCE_TABLE, Table.TIMEKEEPING_ATTENDANCE_TABLE,
    Table.PLAYER_METRIC, Table.TEMP_DATA_TABLE, Table.SETTINGS_TABLE,
}
if GLOBAL_TABLES | TEAM_SCOPED_TABLES != set(Table) or GLOBAL_TABLES & TEAM_SCOPED_TABLES:
    # A new Table member must be consciously classified as global or team-scoped;
    # failing at import time makes the whole test suite catch the omission.
    raise AssertionError('every Table must be classified as exactly one of GLOBAL_TABLES / TEAM_SCOPED_TABLES')


def get_current_season_dates():
    today = datetime.today()
    current_year = today.year

    # Determine if we are in the first half of the year (January to June)
    if today.month < 7:
        # Current season started last year on July 1st
        season_start = datetime(current_year - 1, 7, 1)
        season_end = datetime(current_year, 6, 30)
    else:
        # Current season started this year on July 1st
        season_start = datetime(current_year, 7, 1)
        season_end = datetime(current_year + 1, 6, 30)

    return season_start, season_end


class FirebaseRepository(Repository):
    # The settings table holds a single configuration document under a fixed id, so it can be
    # read/written deterministically without a query (no "more than one" ambiguity).
    SETTINGS_DOC_ID = 'config'

    def __init__(self, api_config: ApiConfig, tables: Tables):
        self.tables = tables
        api_config_path = PathUtils.get_secrets_file_path(api_config.get_key('Firebase', 'credentialsFileName'))
        cred_object = firebase_admin.credentials.Certificate(api_config_path)
        try:
            # initialize_app throws if the default app already exists; reuse it so a second
            # repository instance doesn't crash the process.
            default_app = firebase_admin.get_app()
        except ValueError:
            default_app = firebase_admin.initialize_app(cred_object)
        self.db = firestore.client(default_app)

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
        query_ref = self._collection(table).document(doc_id)
        return query_ref.get()

    def get_user(self, telegram_id_or_doc_id: int | str) -> TelegramUser | None:
        if isinstance(telegram_id_or_doc_id, str):
            res = self.get_document(telegram_id_or_doc_id, Table.USERS_TABLE)
            return TelegramUser.from_dict(res.id, res.to_dict())

        query_ref = self._collection(Table.USERS_TABLE).where(
            filter=FieldFilter("telegramId", "==", telegram_id_or_doc_id))
        res = query_ref.get()
        if len(res) == 0:
            raise ObjectNotFoundException(self.tables.get(Table.USERS_TABLE), telegram_id_or_doc_id)
        if len(res) == 1:
            return TelegramUser.from_dict(res[0].id, res[0].to_dict())
        else:
            raise MoreThanOneObjectFoundException

    def get_user_state(self, user: TelegramUser) -> UsersToState | None:
        user_id = user.doc_id
        query_ref = self._collection(Table.USERS_TO_STATE_TABLE).where(
            filter=FieldFilter("userId", "==", user_id))
        res = query_ref.get()
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
        query_ref = (self._collection(Table.PLAYER_METRIC)
            .where(filter=FieldFilter("userId", "==", user.doc_id))) \
            .where(filter=FieldFilter("insertTimestamp", ">", season_start)) \
            .where(filter=FieldFilter("insertTimestamp", "<", season_end))
        entries = query_ref.get()
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
        doc_ref = self.add(new_player_metric, Table.PLAYER_METRIC)
        return new_player_metric.add_document_id(doc_ref[1].id)

    def get_temp_data(self, user_doc_id: str) -> TempData:
        query_ref = (self._collection(Table.TEMP_DATA_TABLE)
                     .where(filter=FieldFilter("userDocId", "==", user_doc_id)))
        result_list = query_ref.get()
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
        # get all events in table which take place in the future
        now = datetime.now()
        query_ref = (self._collection(table)
                     .where(filter=FieldFilter("timestamp", ">", now)))
        event_list = query_ref.get()
        if len(event_list) == 0:
            return []
        return event_list

    def get_attendance_list(self, doc_id: str, table: Table):
        query_ref = (self._collection(table)
                     .where(filter=FieldFilter("eventId", "==", doc_id)))
        entries = query_ref.get()
        return entries

    def get_attendance(self, user: TelegramUser, event_doc_id: str, table: Table):
        query_ref = self._collection(table) \
            .where(filter=FieldFilter("userId", "==", user.doc_id)) \
            .where(filter=FieldFilter("eventId", "==", event_doc_id))
        result = query_ref.get()
        if len(result) == 0:
            raise ObjectNotFoundException(self.tables.get(table), user.doc_id)
        if len(result) > 1:
            raise MoreThanOneObjectFoundException()
        attendance = result[0]
        return Attendance.from_dict(attendance.id, attendance.to_dict())

    def get_all_user_event_attendance(self, user: TelegramUser, event_type: Event):
        table = self._get_event_attendance_table(event_type)
        query_ref = self._collection(table).where(filter=FieldFilter("userId", "==", user.doc_id))
        entries = query_ref.get()
        return entries

    # Firestore caps the 'in' operator at 30 comparison values, so batch the ids.
    FIRESTORE_IN_LIMIT = 30

    def get_all_event_attendances(self, event_type: Event, relevant_doc_ids: list[str]):
        if len(relevant_doc_ids) == 0:
            return []
        table = self._get_event_attendance_table(event_type)
        entries = []
        for i in range(0, len(relevant_doc_ids), self.FIRESTORE_IN_LIMIT):
            batch = relevant_doc_ids[i:i + self.FIRESTORE_IN_LIMIT]
            query_ref = self._collection(table).where(filter=FieldFilter("eventId", "in", batch))
            entries.extend(query_ref.get())
        return entries

    def get_all_relevant_event_ids(self, event_type: Event):
        table = self._get_event_table(event_type)
        season_start, _ = get_current_season_dates()
        query_ref = (self._collection(table)) \
            .where(filter=FieldFilter("timestamp", ">", season_start)) \
            .where(filter=FieldFilter("timestamp", "<", DateTimeUtils.get_local_now()))
        # filter > start date and < end date
        entries = query_ref.get()
        result = []
        for row in entries:
            result.append(row.id)
        return result

    def get_all_player_metrics(self):
        season_start, season_end = get_current_season_dates()
        query_ref = (self._collection(Table.PLAYER_METRIC)) \
            .where(filter=FieldFilter("insertTimestamp", ">", season_start)) \
            .where(filter=FieldFilter("insertTimestamp", "<", season_end))
        entries = query_ref.get()
        return entries

    def get_users_to_state_by_role(self, role: Role):
        # users_to_state is a global identity table, but role queries are roster views -
        # inherently team-scoped, so they filter on the ambient team (and fail closed
        # without one) even though the collection itself is not partitioned.
        query_ref = self._collection(Table.USERS_TO_STATE_TABLE) \
            .where(filter=FieldFilter("role", "==", role)) \
            .where(filter=FieldFilter("teamId", "==", current_team_id()))
        return query_ref.get()

    def get_admins_to_state(self):
        # Admin is the orthogonal isAdmin flag, not a role - same team-scoped roster
        # view as get_users_to_state_by_role.
        query_ref = self._collection(Table.USERS_TO_STATE_TABLE) \
            .where(filter=FieldFilter("isAdmin", "==", True)) \
            .where(filter=FieldFilter("teamId", "==", current_team_id()))
        return query_ref.get()

    def get_users_to_state_by_team(self, team_id: str):
        # Membership view over the global identity table, keyed explicitly (used by
        # team-lifecycle code that runs OUTSIDE the ambient tenant context).
        query_ref = self._collection(Table.USERS_TO_STATE_TABLE) \
            .where(filter=FieldFilter("teamId", "==", team_id))
        return query_ref.get()

    def has_any_docs(self, table: Table) -> bool:
        return len(self._collection(table).limit(1).get()) > 0

    def delete_team(self, doc_id: str):
        # Firestore does NOT cascade a document delete into its subcollections, so a
        # rolled-back team must purge its team-scoped docs first (a fresh team holds at
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
        query_ref = self._collection(Table.USERS_TO_STATE_TABLE) \
            .where(filter=FieldFilter("role", "==", Role.PLAYER)) \
            .where(filter=FieldFilter("teamId", "==", current_team_id()))
        entries = query_ref.get()
        return entries

    def get_event_attendance_doc_id(self, attendance: Attendance, table: Table):
        query_ref = self._collection(table) \
            .where(filter=FieldFilter("userId", "==", attendance.user_id)) \
            .where(filter=FieldFilter("eventId", "==", attendance.event_id))
        result = query_ref.get()
        if len(result) == 0:
            return None
        if len(result) > 1:
            raise MoreThanOneObjectFoundException(attendance)
        return result[0].id

    ################
    # ADD / UPDATE #
    ################

    def add(self, new_object: DatabaseEntity, table: Table) -> str:
        _, document_reference = self._collection(table).add(new_object.to_dict())
        return document_reference.id

    def update(self, db_object: DatabaseEntity, table: Table):
        self._raise_exception_if_document_not_exists(table, db_object.doc_id)
        self._collection(table).document(db_object.doc_id).update(db_object.to_dict())
        return db_object

    def update_user_state(self, user_to_state: UsersToState):
        self._raise_exception_if_document_not_exists(Table.USERS_TO_STATE_TABLE, user_to_state.doc_id)
        self._collection(Table.USERS_TO_STATE_TABLE).document(user_to_state.doc_id).update(
            {'state': int(user_to_state.state)})

    def update_user_state_via_user_id(self, user_to_state: UsersToState):
        query_ref = self._collection(Table.USERS_TO_STATE_TABLE).where(
            filter=FieldFilter("userId", "==", user_to_state.user_id))
        res = query_ref.get()
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
        query_ref = self._collection(table) \
            .where(filter=FieldFilter("eventId", "==", event_doc_id))
        self._delete_documents(table, query_ref.stream())

    def delete_all_player_metrics(self) -> int:
        return self._delete_documents(Table.PLAYER_METRIC, self._collection(Table.PLAYER_METRIC).stream())

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
        attendance_rows = collection_reference.where(filter=FieldFilter("eventId", "==", doc_id)).get()
        field_update = {"state": 0}
        for row in attendance_rows:
            doc = collection_reference.document(row.id)
            doc.update(field_update)
