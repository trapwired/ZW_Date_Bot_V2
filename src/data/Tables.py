import configparser

from Enums.Event import Event
from Enums.Table import Table

from Utils.ApiConfig import ApiConfig


def initialize_tables(api_config: ApiConfig):
    return {
        Table.GAME_ATTENDANCE_TABLE: api_config.get_key('Tables', 'GAME_ATTENDANCE_TABLE'),
        Table.GAMES_TABLE: api_config.get_key('Tables', 'GAMES_TABLE'),
        Table.USERS_TABLE: api_config.get_key('Tables', 'USERS_TABLE'),
        Table.USERS_TO_STATE_TABLE: api_config.get_key('Tables', 'USERS_TO_STATE_TABLE'),
        Table.TIMEKEEPING_ATTENDANCE_TABLE: api_config.get_key('Tables', 'TIMEKEEPING_ATTENDANCE_TABLE'),
        Table.TIMEKEEPING_TABLE: api_config.get_key('Tables', 'TIMEKEEPING_TABLE'),
        Table.TRAINING_ATTENDANCE_TABLE: api_config.get_key('Tables', 'TRAINING_ATTENDANCE_TABLE'),
        Table.TRAININGS_TABLE: api_config.get_key('Tables', 'TRAININGS_TABLE'),
        Table.PLAYER_METRIC: api_config.get_key('Tables', 'PLAYER_METRIC'),
        Table.TEMP_DATA_TABLE: api_config.get_key('Tables', 'TEMP_DATA'),
        Table.SETTINGS_TABLE: api_config.get_key('Tables', 'SETTINGS_TABLE'),
        Table.TEAMS_TABLE: api_config.get_key('Tables', 'TEAMS_TABLE')
    }


class Tables(object):
    def __init__(self, api_confi: configparser.RawConfigParser):
        self.tables = initialize_tables(api_confi)

    def get(self, table: Table):
        return self.tables[table]


# The per-event-type table pairs, defined once so the repository and DataAccess
# cannot drift apart.
EVENT_TABLES = {Event.GAME: Table.GAMES_TABLE,
                Event.TRAINING: Table.TRAININGS_TABLE,
                Event.TIMEKEEPING: Table.TIMEKEEPING_TABLE}

EVENT_ATTENDANCE_TABLES = {Event.GAME: Table.GAME_ATTENDANCE_TABLE,
                           Event.TRAINING: Table.TRAINING_ATTENDANCE_TABLE,
                           Event.TIMEKEEPING: Table.TIMEKEEPING_ATTENDANCE_TABLE}

# Tenancy classification (ADR 0001): identity and the team registry itself are global -
# team resolution needs the user record before a team is known; everything else is
# team-partitioned and unreachable without a tenant context.
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
