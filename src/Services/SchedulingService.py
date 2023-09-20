import configparser
import datetime

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService

from telegram.ext import ContextTypes

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.MessageType import MessageType
from Enums.UserState import UserState

from Utils.CustomExceptions import ObjectNotFoundException
from Utils import PrintUtils
from Utils import CallbackUtils
from Utils.ApiConfig import ApiConfig


def get_events_in_x_days(all_future_events, individual_game_reminder_frequency):
    relevant_events = []
    for event in all_future_events:
        if (event.timestamp.date() - datetime.date.today()).days in individual_game_reminder_frequency:
            relevant_events.append(event)
    return relevant_events


class SchedulingService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService, api_config: ApiConfig):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.individual_game_reminder_frequency = api_config.get_int_list('Scheduling', 'GAME_INDIVIDUAL')

    async def send_individual_game_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            all_future_games = self.data_access.get_ordered_games()
            all_relevant_games = get_events_in_x_days(all_future_games, self.individual_game_reminder_frequency)

            all_players = self.data_access.get_all_players()

            game_to_unsure_players = dict()
            for game in all_relevant_games:
                _, _, unsure = self.data_access.get_stats_event(game.doc_id, Event.GAME)
                unsure_players = []
                for player_id in unsure:
                    player = next((x for x in all_players if x.doc_id == player_id), None)
                    if player is None:
                        raise ObjectNotFoundException(player)
                    unsure_players.append(player)
                game_to_unsure_players[game] = unsure_players

            unsure_player_to_games = dict()
            for game, player_ids in game_to_unsure_players.items():
                for player in player_ids:
                    if player not in unsure_player_to_games:
                        unsure_player_to_games[player] = []
                    if len(unsure_player_to_games[player]) <= 3:
                        unsure_player_to_games[player].append(game)

            message_sent_count = 0
            for player, game_list in unsure_player_to_games.items():
                message_sent_count += await self.send_game_enroll_reminder(player, game_list)

            message = f'Sent out a total of {message_sent_count} game reminders to {len(unsure_player_to_games)} Player(s)'
            await self.telegram_service.send_maintainer_message(message)

        except Exception as e:
            await self.telegram_service.send_maintainer_message(
                'Exception caught in SchedulingService.send_individual_game_reminders()',
                e)

    async def send_game_enroll_reminder(self, player, game_list) -> int:
        messages_sent_count = 0
        await self.telegram_service.send_message(
            update=player,
            all_buttons=None,
            message_type=MessageType.ENROLLMENT_REMINDER)

        for game in game_list:
            pretty_print_game = PrintUtils.pretty_print(game, AttendanceState.UNSURE)
            reply_markup = CallbackUtils.get_reply_markup(UserState.EDIT, Event.GAME, game.doc_id)
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=pretty_print_game,
                reply_markup=reply_markup)
            messages_sent_count += 1

        return messages_sent_count

    async def send_game_summary(self, context: ContextTypes.DEFAULT_TYPE):
        all_future_games = self.data_access.get_ordered_games()
        games_in_27_days = get_events_in_x_days(all_future_games, [27])

        for game in games_in_27_days:
            stats = self.data_access.get_stats_event(game.doc_id, Event.GAME)
            stats_with_names = self.data_access.get_names(stats)
            pretty_print_game = PrintUtils.pretty_print(game)
            message = PrintUtils.pretty_print_event_summary(stats_with_names, pretty_print_game)
            message = 'Hey, just a short summary for the game in 4 weeks: \n\n' + message
            await self.telegram_service.send_info_message_to_trainers(message)
