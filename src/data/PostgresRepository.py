"""Postgres implementation of the storage seam (Stage B).

Semantics mirror FirebaseRepository method for method - the contract tests in
tests/contract/ run both implementations' behavior against the seam's rules.

Shape notes:
- Entities keep speaking camelCase dicts (their from_dict/to_dict); each table
  spec maps those keys to snake_case columns and back. Query methods return Row
  records satisfying the seam's row duck type (.id / .to_dict()).
- The three Firestore attendance collections are ONE attendance table with an
  event_type discriminator, injected on write and filtered on read.
- Tenancy: team-scoped tables carry a team_id column filled from the ambient
  TenantContext (the Postgres analogue of FirebaseRepository._collection).
"""
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from importlib import resources

import psycopg
from psycopg_pool import ConnectionPool

from data.Repository import Repository
from data.TenantContext import current_team_id

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
from Utils.ApiConfig import ApiConfig
from Utils import DateTimeUtils

SETTINGS_DOC_ID = 'config'


@dataclass(frozen=True)
class Row:
    """The seam's row duck type (see Repository docstring)."""
    id: str
    data: dict

    def to_dict(self) -> dict:
        return self.data


@dataclass(frozen=True)
class TableSpec:
    sql_table: str
    columns: dict  # entity dict key (camelCase) -> column (snake_case)
    team_scoped: bool
    event_type: int | None = None  # attendance discriminator


_EVENT_COLUMNS = {'timestamp': 'timestamp', 'location': 'location'}
_ATTENDANCE_COLUMNS = {'userId': 'user_id', 'eventId': 'event_id', 'state': 'state'}

TABLE_SPECS = {
    Table.USERS_TABLE: TableSpec('users', {
        'telegramId': 'telegram_id', 'firstname': 'firstname', 'lastname': 'lastname'}, team_scoped=False),
    Table.USERS_TO_STATE_TABLE: TableSpec('users_to_state', {
        'userId': 'user_id', 'state': 'state', 'additionalInformation': 'additional_info',
        'role': 'role', 'isAdmin': 'is_admin', 'teamId': 'team_id', 'language': 'language'}, team_scoped=False),
    Table.TEAMS_TABLE: TableSpec('teams', {
        'name': 'name', 'groupChatId': 'group_chat_id', 'spectatorPassword': 'spectator_password',
        'trainersGames': 'trainers_games', 'trainersTraining': 'trainers_training',
        'inviteTokens': 'invite_tokens', 'language': 'language'}, team_scoped=False),
    Table.GAMES_TABLE: TableSpec('games', {**_EVENT_COLUMNS, 'opponent': 'opponent'}, team_scoped=True),
    Table.TRAININGS_TABLE: TableSpec('trainings', dict(_EVENT_COLUMNS), team_scoped=True),
    Table.TIMEKEEPING_TABLE: TableSpec('timekeepings', {
        **_EVENT_COLUMNS, 'people_required': 'people_required'}, team_scoped=True),
    Table.GAME_ATTENDANCE_TABLE: TableSpec('attendance', dict(_ATTENDANCE_COLUMNS),
                                           team_scoped=True, event_type=int(Event.GAME)),
    Table.TRAINING_ATTENDANCE_TABLE: TableSpec('attendance', dict(_ATTENDANCE_COLUMNS),
                                               team_scoped=True, event_type=int(Event.TRAINING)),
    Table.TIMEKEEPING_ATTENDANCE_TABLE: TableSpec('attendance', dict(_ATTENDANCE_COLUMNS),
                                                  team_scoped=True, event_type=int(Event.TIMEKEEPING)),
    Table.PLAYER_METRIC: TableSpec('player_metric', {
        'userId': 'user_id', 'gameRemindersSent': 'game_reminders_sent',
        'trainingRemindersSent': 'training_reminders_sent',
        'timekeepingRemindersSent': 'timekeeping_reminders_sent',
        'insertTimestamp': 'insert_timestamp'}, team_scoped=True),
    Table.TEMP_DATA_TABLE: TableSpec('temp_data', {
        'userDocId': 'user_doc_id', 'timestamp': 'timestamp', 'location': 'location',
        'opponent': 'opponent', 'chatId': 'chat_id', 'queryId': 'query_id', 'step': 'step',
        'eventType': 'event_type', 'promptMessageId': 'prompt_message_id'}, team_scoped=True),
    Table.SETTINGS_TABLE: TableSpec('settings', {'website': 'website'}, team_scoped=True),
}
if set(TABLE_SPECS) != set(Table):
    raise AssertionError('every Table must have a TableSpec')

DEFAULT_DSN = 'postgresql://zwdatebot:zwdatebot@localhost:5432/zwdatebot'


def _to_sql_value(value):
    # psycopg refuses IntEnums and pandas Timestamps; both flow in from entities.
    if isinstance(value, IntEnum):
        return int(value)
    if value is not None and hasattr(value, 'to_pydatetime'):
        return value.to_pydatetime()
    return value


class PostgresRepository(Repository):

    def __init__(self, api_config: ApiConfig):
        dsn = api_config.get_key('Database', 'dsn', default=DEFAULT_DSN)
        # Session TZ pinned to UTC: naive datetimes from the wizard are interpreted
        # exactly like Firestore interpreted them, so wall-clock times survive.
        self.pool = ConnectionPool(dsn, min_size=1, max_size=4, open=True,
                                   kwargs={'options': '-c timezone=UTC'})
        self._apply_schema()

    def _apply_schema(self):
        schema = resources.files('data').joinpath('schema.sql').read_text(encoding='utf8')
        self._execute(schema)

    def _execute(self, sql: str, params=None):
        with self.pool.connection() as connection:
            return connection.execute(sql, params)

    @staticmethod
    def _spec(table: Table) -> TableSpec:
        return TABLE_SPECS[table]

    @staticmethod
    def _make_row(spec: TableSpec, columns: list[str], values) -> Row:
        record = dict(zip(columns, values))
        data = {key: record[column] for key, column in spec.columns.items() if column in record}
        return Row(id=record['id'], data=data)

    def _select(self, table: Table, where: str = '', params: tuple = (), scoped: bool = True) -> list[Row]:
        spec = self._spec(table)
        conditions, condition_params = self._scope_conditions(spec, scoped)
        if where:
            conditions.append(where)
            condition_params.extend(params)
        sql = f'SELECT * FROM {spec.sql_table}'
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
        with self.pool.connection() as connection:
            cursor = connection.execute(sql, condition_params)
            columns = [d.name for d in cursor.description]
            return [self._make_row(spec, columns, values) for values in cursor.fetchall()]

    @staticmethod
    def _scope_conditions(spec: TableSpec, scoped: bool) -> tuple[list, list]:
        conditions, params = [], []
        if spec.team_scoped and scoped:
            # Fail-closed like FirebaseRepository._collection: no ambient team, no data.
            conditions.append('team_id = %s')
            params.append(current_team_id())
        if spec.event_type is not None:
            conditions.append('event_type = %s')
            params.append(spec.event_type)
        return conditions, params

    def _insert(self, table: Table, data: dict) -> str:
        spec = self._spec(table)
        columns, values = [], []
        for key, value in data.items():
            columns.append(spec.columns[key])
            values.append(_to_sql_value(value))
        if spec.team_scoped:
            columns.append('team_id')
            values.append(current_team_id())
        if spec.event_type is not None:
            columns.append('event_type')
            values.append(spec.event_type)
        placeholders = ', '.join(['%s'] * len(columns))
        sql = f'INSERT INTO {spec.sql_table} ({", ".join(columns)}) VALUES ({placeholders}) RETURNING id'
        with self.pool.connection() as connection:
            return connection.execute(sql, values).fetchone()[0]

    def _update_by_id(self, table: Table, doc_id: str, data: dict):
        spec = self._spec(table)
        assignments, values = [], []
        for key, value in data.items():
            assignments.append(f'{spec.columns[key]} = %s')
            values.append(_to_sql_value(value))
        conditions, condition_params = self._scope_conditions(spec, scoped=True)
        conditions.insert(0, 'id = %s')
        condition_params.insert(0, doc_id)
        sql = f'UPDATE {spec.sql_table} SET {", ".join(assignments)} WHERE {" AND ".join(conditions)}'
        result = self._execute(sql, values + condition_params)
        if result.rowcount == 0:
            raise ObjectNotFoundException(spec.sql_table, doc_id)

    def _delete_by_id(self, table: Table, doc_id: str):
        spec = self._spec(table)
        conditions, params = self._scope_conditions(spec, scoped=True)
        conditions.insert(0, 'id = %s')
        params.insert(0, doc_id)
        self._execute(f'DELETE FROM {spec.sql_table} WHERE {" AND ".join(conditions)}', params)

    #######
    # GET #
    #######

    def get_document(self, doc_id: str, table: Table):
        rows = self._select(table, 'id = %s', (doc_id,))
        if not rows:
            raise ObjectNotFoundException(self._spec(table).sql_table, doc_id)
        return rows[0]

    def get_user(self, telegram_id_or_doc_id: int | str) -> TelegramUser | None:
        if isinstance(telegram_id_or_doc_id, str):
            row = self.get_document(telegram_id_or_doc_id, Table.USERS_TABLE)
            return TelegramUser.from_dict(row.id, row.to_dict())
        rows = self._select(Table.USERS_TABLE, 'telegram_id = %s', (telegram_id_or_doc_id,))
        if len(rows) == 0:
            raise ObjectNotFoundException('users', telegram_id_or_doc_id)
        if len(rows) > 1:
            raise MoreThanOneObjectFoundException
        return TelegramUser.from_dict(rows[0].id, rows[0].to_dict())

    def get_user_state(self, user: TelegramUser) -> UsersToState | None:
        rows = self._select(Table.USERS_TO_STATE_TABLE, 'user_id = %s', (user.doc_id,))
        if len(rows) == 1:
            return UsersToState.from_dict(rows[0].id, rows[0].to_dict())
        if len(rows) > 1:
            # Duplicate state docs for one user are data corruption, not a not-found.
            raise MoreThanOneObjectFoundException()
        raise ObjectNotFoundException('users_to_state', user.doc_id)

    def get_game(self, doc_id: str) -> Game | None:
        row = self.get_document(doc_id, Table.GAMES_TABLE)
        return Game.from_dict(row.id, row.to_dict())

    def get_training(self, doc_id: str) -> Training | None:
        row = self.get_document(doc_id, Table.TRAININGS_TABLE)
        return Training.from_dict(row.id, row.to_dict())

    def get_timekeeping(self, doc_id: str) -> TimekeepingEvent | None:
        row = self.get_document(doc_id, Table.TIMEKEEPING_TABLE)
        return TimekeepingEvent.from_dict(row.id, row.to_dict())

    def get_team(self, doc_id: str) -> Team:
        row = self.get_document(doc_id, Table.TEAMS_TABLE)
        return Team.from_dict(row.id, row.to_dict())

    def get_all_teams(self) -> list[Team]:
        rows = self._select(Table.TEAMS_TABLE)
        return [Team.from_dict(row.id, row.to_dict()) for row in rows]

    def get_player_metric(self, user: TelegramUser):
        season_start, season_end = get_current_season_dates()
        rows = self._select(Table.PLAYER_METRIC,
                            'user_id = %s AND insert_timestamp > %s AND insert_timestamp < %s',
                            (user.doc_id, season_start, season_end))
        if len(rows) == 1:
            return PlayerMetric.from_dict(rows[0].id, rows[0].to_dict())
        if len(rows) > 1:
            # Self-heal duplicate season records exactly like the Firestore backend.
            for row in rows[1:]:
                self._delete_by_id(Table.PLAYER_METRIC, row.id)
            return PlayerMetric.from_dict(rows[0].id, rows[0].to_dict())
        new_player_metric = PlayerMetric(user.doc_id, 0, 0, 0, DateTimeUtils.get_local_now())
        doc_id = self.add(new_player_metric, Table.PLAYER_METRIC)
        return new_player_metric.add_document_id(doc_id)

    def get_temp_data(self, user_doc_id: str) -> TempData:
        rows = self._select(Table.TEMP_DATA_TABLE, 'user_doc_id = %s', (user_doc_id,))
        if len(rows) == 0:
            raise NoTempDataFoundException()
        if len(rows) > 1:
            raise TooManyObjectsFoundException()
        return TempData.from_dict(rows[0].id, rows[0].to_dict())

    def get_settings(self) -> Settings | None:
        rows = self._select(Table.SETTINGS_TABLE, 'id = %s', (SETTINGS_DOC_ID,))
        if not rows:
            return None
        return Settings.from_dict(rows[0].id, rows[0].to_dict())

    def set_settings(self, settings: Settings):
        # Upsert: creates the single settings row on first save, overwrites afterwards.
        self._execute(
            'INSERT INTO settings (id, team_id, website) VALUES (%s, %s, %s) '
            'ON CONFLICT (team_id, id) DO UPDATE SET website = EXCLUDED.website',
            (SETTINGS_DOC_ID, current_team_id(), settings.website))

    def get_future_events(self, table: Table) -> list:
        return self._select(table, 'timestamp > %s', (datetime.now(),))

    def get_attendance_list(self, doc_id: str, table: Table):
        return self._select(table, 'event_id = %s', (doc_id,))

    def get_attendance(self, user: TelegramUser, event_doc_id: str, table: Table):
        rows = self._select(table, 'user_id = %s AND event_id = %s', (user.doc_id, event_doc_id))
        if len(rows) == 0:
            raise ObjectNotFoundException(self._spec(table).sql_table, user.doc_id)
        if len(rows) > 1:
            raise MoreThanOneObjectFoundException()
        return Attendance.from_dict(rows[0].id, rows[0].to_dict())

    def get_all_user_event_attendance(self, user: TelegramUser, event_type: Event):
        return self._select(_attendance_table(event_type), 'user_id = %s', (user.doc_id,))

    def get_all_event_attendances(self, event_type: Event, relevant_doc_ids: list[str]):
        if len(relevant_doc_ids) == 0:
            return []
        return self._select(_attendance_table(event_type), 'event_id = ANY(%s)', (relevant_doc_ids,))

    def get_all_relevant_event_ids(self, event_type: Event):
        season_start, _ = get_current_season_dates()
        rows = self._select(_EVENT_TABLE_BY_TYPE[event_type], 'timestamp > %s AND timestamp < %s',
                            (season_start, DateTimeUtils.get_local_now()))
        return [row.id for row in rows]

    def get_all_player_metrics(self):
        season_start, season_end = get_current_season_dates()
        return self._select(Table.PLAYER_METRIC, 'insert_timestamp > %s AND insert_timestamp < %s',
                            (season_start, season_end))

    def get_users_to_state_by_role(self, role: Role):
        # Global identity table, but role queries are roster views - team-filtered
        # on the ambient tenant (and fail closed without one), like Firestore.
        return self._select(Table.USERS_TO_STATE_TABLE, 'role = %s AND team_id = %s',
                            (int(role), current_team_id()))

    def get_admins_to_state(self):
        return self._select(Table.USERS_TO_STATE_TABLE, 'is_admin = true AND team_id = %s',
                            (current_team_id(),))

    def get_users_to_state_by_team(self, team_id: str):
        return self._select(Table.USERS_TO_STATE_TABLE, 'team_id = %s', (team_id,))

    def get_all_active_players_to_state(self):
        return self._select(Table.USERS_TO_STATE_TABLE, 'role = %s AND team_id = %s',
                            (int(Role.PLAYER), current_team_id()))

    def has_any_docs(self, table: Table) -> bool:
        return len(self._select(table)) > 0

    def delete_team(self, doc_id: str):
        # Unlike Firestore there is no subcollection orphaning, but the same promise
        # holds: a rolled-back team leaves no scoped rows behind.
        scoped_tables = {spec.sql_table for spec in TABLE_SPECS.values() if spec.team_scoped}
        with self.pool.connection() as connection:
            for sql_table in scoped_tables:
                connection.execute(f'DELETE FROM {sql_table} WHERE team_id = %s', (doc_id,))
            connection.execute('DELETE FROM teams WHERE id = %s', (doc_id,))

    def get_event_attendance_doc_id(self, attendance: Attendance, table: Table):
        rows = self._select(table, 'user_id = %s AND event_id = %s',
                            (attendance.user_id, attendance.event_id))
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            raise MoreThanOneObjectFoundException(attendance)
        return rows[0].id

    ################
    # ADD / UPDATE #
    ################

    def add(self, new_object: DatabaseEntity, table: Table) -> str:
        return self._insert(table, new_object.to_dict())

    def update(self, db_object: DatabaseEntity, table: Table):
        self._update_by_id(table, db_object.doc_id, db_object.to_dict())
        return db_object

    def update_user_state(self, user_to_state: UsersToState):
        self._update_by_id(Table.USERS_TO_STATE_TABLE, user_to_state.doc_id,
                           {'state': int(user_to_state.state)})

    def update_user_state_via_user_id(self, user_to_state: UsersToState):
        rows = self._select(Table.USERS_TO_STATE_TABLE, 'user_id = %s', (user_to_state.user_id,))
        if len(rows) == 1:
            updated_user_to_state = user_to_state.add_document_id(rows[0].id)
            self.update_user_state(updated_user_to_state)
        elif len(rows) > 1:
            raise MoreThanOneObjectFoundException()
        else:
            raise ObjectNotFoundException('users_to_state', user_to_state.user_id)

    def update_user_via_telegram_id(self, user: TelegramUser):
        user_id = self.get_user(user.telegramId).doc_id
        user.add_document_id(user_id)
        return self.update(user, Table.USERS_TABLE)

    ##########
    # DELETE #
    ##########

    def delete_temp_data(self, temp_data: TempData):
        self._delete_by_id(Table.TEMP_DATA_TABLE, temp_data.doc_id)

    def delete_game(self, doc_id: str):
        self._delete_by_id(Table.GAMES_TABLE, doc_id)

    def delete_training(self, doc_id: str):
        self._delete_by_id(Table.TRAININGS_TABLE, doc_id)

    def delete_timekeeping(self, doc_id: str):
        self._delete_by_id(Table.TIMEKEEPING_TABLE, doc_id)

    def delete_event_attendances(self, event_type: Event, event_doc_id: str):
        spec = self._spec(_attendance_table(event_type))
        self._execute(
            f'DELETE FROM {spec.sql_table} WHERE team_id = %s AND event_type = %s AND event_id = %s',
            (current_team_id(), spec.event_type, event_doc_id))

    def delete_all_player_metrics(self) -> int:
        result = self._execute('DELETE FROM player_metric WHERE team_id = %s', (current_team_id(),))
        return result.rowcount

    ########
    # ELSE #
    ########

    def reset_all_player_event_attendance(self, doc_id: str, table: Table):
        spec = self._spec(table)
        self._execute(
            f'UPDATE {spec.sql_table} SET state = 0 '
            f'WHERE team_id = %s AND event_type = %s AND event_id = %s',
            (current_team_id(), spec.event_type, doc_id))


_EVENT_TABLE_BY_TYPE = {
    Event.GAME: Table.GAMES_TABLE,
    Event.TRAINING: Table.TRAININGS_TABLE,
    Event.TIMEKEEPING: Table.TIMEKEEPING_TABLE,
}


def _attendance_table(event_type: Event) -> Table:
    return {
        Event.GAME: Table.GAME_ATTENDANCE_TABLE,
        Event.TRAINING: Table.TRAINING_ATTENDANCE_TABLE,
        Event.TIMEKEEPING: Table.TIMEKEEPING_ATTENDANCE_TABLE,
    }[event_type]
