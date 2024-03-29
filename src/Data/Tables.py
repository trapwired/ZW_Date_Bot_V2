import configparser

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
        Table.TEMP_DATA_TABLE: api_config.get_key('Tables', 'TEMP_DATA')
    }


class Tables(object):
    def __init__(self, api_confi: configparser.RawConfigParser):
        self.tables = initialize_tables(api_confi)

    def get(self, table: Table):
        return self.tables[table]
