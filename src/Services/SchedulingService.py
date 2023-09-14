import configparser

from Data.DataAccess import DataAccess
from Services.TelegramService import TelegramService
from telegram.ext import ContextTypes


def initialize_reminder_frequency(frequencies: str):
    return [int(x.strip()) for x in frequencies.split(',')]


class SchedulingService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService,
                 api_config: configparser.RawConfigParser):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.individual_game_reminder_frequency = initialize_reminder_frequency(
            api_config['Scheduling']['GAME_INDIVIDUAL'])
        print(self.individual_game_reminder_frequency)

    async def send_individual_game_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        print('here we are')
        # get all games in self.individual_game_reminder_frequency days

        # get all players, store in list

        # create dict: (Game, AllPlayersList)

        # for each game, get attendances,
        # loop over Attendance: remove from AllPlayersList all yes / no

        # create dict: (telegram_id, [Game])
        # loop over all games-dict (sorted by due date)
        # loop over all attendances, add Game to respective player_dict, add max of 3

        # foreach kvp: send pretty-print_game, including callback buttons for each
        # 1 send msg: Please register
        # 2 send for all 3 string + callbak
