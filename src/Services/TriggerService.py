from Data.DataAccess import DataAccess

from Triggers.TriggerPayload import TriggerPayload
from Triggers.AttendanceUpdateTrigger import AttendanceUpdateTrigger

from Services.TelegramService import TelegramService

from Enums.AttendanceState import AttendanceState

from Enums.Event import Event


class TriggerService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.triggers = self.initialize_triggers(data_access)

    def initialize_triggers(self, data_access: DataAccess):
        triggers = []

        pre_condition = lambda tp: tp.attendance_is(AttendanceState.NO) and tp.event_is(Event.GAME)
        condition = lambda tp: data_access.get_num_of_no_of_event(tp.doc_id, tp.event_type) > 8
        notify_action = lambda tp: self.send_event_message(tp)
        new_trigger = AttendanceUpdateTrigger(pre_condition, condition, notify_action)
        triggers.append(new_trigger)

        return triggers

    def check_triggers(self, trigger_payload: TriggerPayload):
        for trigger in self.triggers:
            if trigger.check(trigger_payload):
                trigger.notify_action(trigger_payload)

    def send_event_message(self, trigger_payload: TriggerPayload):
        # get event
        # pretty print
        # assemble message
        # await telegram_service.send it
