import logging

from data.DataAccess import DataAccess

from framework.Triggers.TriggerPayload import TriggerPayload
from framework.Triggers.AttendanceUpdateTrigger import AttendanceUpdateTrigger

from framework.Services.TelegramService import TelegramService

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from domain.GameRules import has_too_few_available_players

from Utils import PrintUtils


class TriggerService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.triggers = self.initialize_triggers(data_access)
        self.data_access = data_access
        self.telegram_service = telegram_service

    def initialize_triggers(self, data_access: DataAccess):
        triggers = []

        # Trigger: warn trainers when cancellations leave too few players available
        # (yes or unsure) for a game; deliberately fires again on every further no
        # while availability stays low
        pre_condition = lambda tp: tp.attendance_is(AttendanceState.NO) and tp.event_is(Event.GAME)
        condition = lambda tp: has_too_few_available_players(
            data_access.get_num_of_available_players(tp.doc_id, tp.event_type))
        new_trigger = AttendanceUpdateTrigger(pre_condition, condition, self.send_low_availability_warning)
        triggers.append(new_trigger)

        # Trigger: notify if both keepers said no on event

        return triggers

    async def check_triggers(self, trigger_payload: TriggerPayload):
        for trigger in self.triggers:
            if trigger.check(trigger_payload):
                logging.info('Trigger fired: %s for event %s',
                             type(trigger).__name__, trigger_payload.doc_id)
                await trigger.notify_action(trigger_payload)

    async def send_low_availability_warning(self, trigger_payload: TriggerPayload):
        available = self.data_access.get_num_of_available_players(trigger_payload.doc_id,
                                                                  trigger_payload.event_type)
        message = f'So many players said no that only {available} players are still available (yes or unsure)'
        await self.send_event_message(trigger_payload, message)

    async def send_event_message(self, trigger_payload: TriggerPayload, msg: str):
        game = self.data_access.get_game(trigger_payload.doc_id)
        pretty_game = PrintUtils.pretty_print(game)
        message = 'Trigger: For the following game:\n\n' + pretty_game + '\n\n' + msg
        await self.telegram_service.send_info_message_to_trainers(message, Event.GAME)
