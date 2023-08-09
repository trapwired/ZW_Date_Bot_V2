import configparser

from Enums.Table import Table


def initialize_tables(api_config: configparser.RawConfigParser):
    return {
        Table.GAME_ATTENDANCE_TABLE: api_config['Tables']['GAME_ATTENDANCE_TABLE'],
        Table.GAMES_TABLE: api_config['Tables']['GAMES_TABLE'],
        Table.PLAYERS_TABLE: api_config['Tables']['PLAYERS_TABLE'],
        Table.PLAYERS_TO_STATE_TABLE: api_config['Tables']['PLAYERS_TO_STATE_TABLE'],
        Table.TIMEKEEPING_ATTENDANCE_TABLE: api_config['Tables']['TIMEKEEPING_ATTENDANCE_TABLE'],
        Table.TIMEKEEPING_TABLE: api_config['Tables']['TIMEKEEPING_TABLE'],
        Table.TRAINING_ATTENDANCE_TABLE: api_config['Tables']['TRAINING_ATTENDANCE_TABLE'],
        Table.TRAININGS_TABLE: api_config['Tables']['TRAININGS_TABLE']
    }


class Tables(object):
    def __init__(self, api_confi: configparser.RawConfigParser):
        self.tables = initialize_tables(api_confi)

    def get(self, table: Table):
        return self.tables[table]