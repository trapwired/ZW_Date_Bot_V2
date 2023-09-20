from Data.DataAccess import DataAccess

from Triggers.TriggerPayload import TriggerPayload
from Triggers.AttendanceUpdateTrigger import AttendanceUpdateTrigger

from Services.TelegramService import TelegramService

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from Utils import PrintUtils


class TriggerService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.triggers = self.initialize_triggers(data_access)
        self.data_access = data_access
        self.telegram_service = telegram_service

    def initialize_triggers(self, data_access: DataAccess):
        triggers = []

        # Trigger: notify if more than 8 ppl said no on event
        pre_condition = lambda tp: tp.attendance_is(AttendanceState.NO) and tp.event_is(Event.GAME)
        condition = lambda tp: data_access.get_num_of_no_of_event(tp.doc_id, tp.event_type) > 7
        message = 'More than 7 players indicated no - so we can only be a maximum of 9 players'
        notify_action = lambda tp: self.send_event_message(tp, message)
        new_trigger = AttendanceUpdateTrigger(pre_condition, condition, notify_action, message)
        triggers.append(new_trigger)

        # Trigger: notify if both keepers said no on event

        return triggers

    async def check_triggers(self, trigger_payload: TriggerPayload):
        for trigger in self.triggers:
            if trigger.check(trigger_payload):
                await trigger.notify_action(trigger_payload)

    async def send_event_message(self, trigger_payload: TriggerPayload, msg: str):
        game = self.data_access.get_game(trigger_payload.doc_id)
        pretty_game = PrintUtils.pretty_print(game)
        message = 'FYI: For the following game:\n\n' + pretty_game + '\n\n' + msg
        await self.telegram_service.send_info_message_to_trainers(message)
