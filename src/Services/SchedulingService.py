import datetime
import random

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

from databaseEntities.TelegramUser import TelegramUser


def get_events_in_x_days(all_future_events, reminder_frequency):
    relevant_events = []
    for event in all_future_events:
        if (event.timestamp.date() - datetime.date.today()).days in reminder_frequency:
            relevant_events.append(event)
    return relevant_events


def get_players_from_doc_ids(id_list: [str], all_players: [TelegramUser]) -> [TelegramUser]:
    result = []
    for player_id in id_list:
        player = next((x for x in all_players if x.doc_id == player_id), None)
        if player is None:
            raise ObjectNotFoundException(player)
        result.append(player)
    return result


class SchedulingService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService, api_config: ApiConfig):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.individual_game_reminder_frequency = api_config.get_int_list('Scheduling', 'GAME_INDIVIDUAL')
        self.individual_training_reminder_frequency = api_config.get_int_list('Scheduling', 'TRAINING_INDIVIDUAL')
        self.individual_timekeeping_reminder_frequency = api_config.get_int_list('Scheduling', 'TIMEKEEPING_INDIVIDUAL')

    async def send_individual_game_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_individual_event_reminders(Event.GAME)

    async def send_individual_training_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_individual_event_reminders(Event.TRAINING)

    async def send_individual_tke_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            all_future_events = self.get_ordered_event(Event.TIMEKEEPING)
            reminder_frequency = self.get_reminder_frequency(Event.TIMEKEEPING)
            all_relevant_events = get_events_in_x_days(all_future_events, reminder_frequency)

            all_players = self.data_access.get_all_players()

            event_to_unsure_players_and_yes = dict()
            already_said_yes = set()
            for event in all_relevant_events:
                yes_ids, _, unsure_ids = self.data_access.get_stats_event(event.doc_id, Event.TIMEKEEPING)
                yes = get_players_from_doc_ids(yes_ids, all_players)

                already_said_yes.update(yes)

                if len(yes) < event.people_required:
                    event_to_unsure_players_and_yes[event] = get_players_from_doc_ids(unsure_ids, all_players), yes

            event_to_unsure_players = dict()
            for event, (unsure_players, yes) in event_to_unsure_players_and_yes.items():
                new_unsure_players = list(p for p in unsure_players if p not in already_said_yes)
                random.shuffle(new_unsure_players)
                people_needed = max(0, event.people_required - len(yes))
                event_to_unsure_players[event] = new_unsure_players[:people_needed]


            unsure_player_to_event = dict()
            for event, players in event_to_unsure_players.items():
                for player in players:
                    if player not in unsure_player_to_event:
                        unsure_player_to_event[player] = []
                    if len(unsure_player_to_event[player]) <= 3:
                        unsure_player_to_event[player].append(event)

            if len(unsure_player_to_event) == 0:
                return

            message_sent_count = 0
            for player, event_list in unsure_player_to_event.items():
                message_sent_count += await self.send_event_enroll_reminder(player, event_list, Event.TIMEKEEPING)

            message = f'Sent out a total of {message_sent_count} timekeeping reminders to {len(unsure_player_to_event)} Player(s)'
            await self.telegram_service.send_maintainer_message(message)
        except Exception as e:
            await self.telegram_service.send_maintainer_message(
                'Exception caught in SchedulingService.send_individual_tke_reminders()',
                e)

    async def _send_individual_event_reminders(self, event_type: Event):
        try:
            all_future_events = self.get_ordered_event(event_type)
            reminder_frequency = self.get_reminder_frequency(event_type)
            all_relevant_events = get_events_in_x_days(all_future_events, reminder_frequency)

            all_players = self.data_access.get_all_players()

            event_to_unsure_players = dict()
            for event in all_relevant_events:
                _, _, unsure_ids = self.data_access.get_stats_event(event.doc_id, event_type)
                event_to_unsure_players[event] = get_players_from_doc_ids(unsure_ids, all_players)

            unsure_player_to_event = dict()
            for event, player_ids in event_to_unsure_players.items():
                for player in player_ids:
                    if player not in unsure_player_to_event:
                        unsure_player_to_event[player] = []
                    if len(unsure_player_to_event[player]) <= 3:
                        unsure_player_to_event[player].append(event)

            if len(unsure_player_to_event) == 0:
                return

            message_sent_count = 0
            for player, event_list in unsure_player_to_event.items():
                message_sent_count += await self.send_event_enroll_reminder(player, event_list, event_type)

            message = f'Sent out a total of {message_sent_count} {event_type.name.lower()} reminders to {len(unsure_player_to_event)} Player(s)'
            await self.telegram_service.send_maintainer_message(message)

        except Exception as e:
            await self.telegram_service.send_maintainer_message(
                'Exception caught in SchedulingService._send_individual_event_reminders()',
                e)

    async def send_event_enroll_reminder(self, player, event_list, event_type: Event) -> int:
        messages_sent_count = 0
        await self.telegram_service.send_message(
            update=player,
            all_buttons=None,
            message_type=MessageType.ENROLLMENT_REMINDER)

        for event in event_list:
            pretty_print_event = PrintUtils.pretty_print(event, AttendanceState.UNSURE)
            reply_markup = CallbackUtils.get_reply_markup(UserState.EDIT, event_type, event.doc_id)
            message_text = event_type.name.lower().title() + ' | ' + pretty_print_event
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)
            messages_sent_count += 1

        return messages_sent_count

    async def send_game_summary(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_event_summary(Event.GAME)

    async def send_training_summary(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_event_summary(Event.TRAINING)

    async def send_timekeeping_summary(self, context: ContextTypes.DEFAULT_TYPE):
        await self._send_event_summary(Event.TIMEKEEPING)

    async def _send_event_summary(self, event_type: Event):
        try:
            all_future_events = self.get_ordered_event(event_type)
            reminder_days = self.get_summary_reminder_day(event_type)
            events_to_remind = get_events_in_x_days(all_future_events, reminder_days)

            for event in events_to_remind:
                stats = self.data_access.get_stats_event(event.doc_id, event_type)
                stats_with_names = self.data_access.get_names(stats)
                pretty_print_event = PrintUtils.pretty_print(event)
                message = PrintUtils.pretty_print_event_summary(stats_with_names, pretty_print_event, event_type)
                message = f'Hey, just a short summary for the upcoming {event_type.name.lower()} in {reminder_days[0]}' \
                          f' days: \n\n' + message
                await self.telegram_service.send_info_message_to_trainers(message, event_type)

        except Exception as e:
            await self.telegram_service.send_maintainer_message(
                'Exception caught in SchedulingService.send_event_summary()',
                e)

    def get_ordered_event(self, event_type: Event):
        match event_type:
            case Event.GAME:
                return self.data_access.get_ordered_games()
            case Event.TRAINING:
                return self.data_access.get_ordered_trainings()
            case Event.TIMEKEEPING:
                return self.data_access.get_ordered_timekeepings()
        return []

    def get_reminder_frequency(self, event_type: Event):
        match event_type:
            case Event.GAME:
                return self.individual_game_reminder_frequency
            case Event.TRAINING:
                return self.individual_training_reminder_frequency
            case Event.TIMEKEEPING:
                return self.individual_timekeeping_reminder_frequency
        return []

    def get_summary_reminder_day(self, event_type):
        match event_type:
            case Event.GAME:
                return [min(self.individual_game_reminder_frequency) - 1]
            case Event.TRAINING:
                return [min(self.individual_training_reminder_frequency) - 1]
            case Event.TIMEKEEPING:
                return [min(self.individual_timekeeping_reminder_frequency) - 1]
        return []
