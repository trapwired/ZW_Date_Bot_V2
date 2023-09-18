from Data.DataAccess import DataAccess

from Triggers.TriggerPayload import TriggerPayload

from Services.TelegramService import TelegramService


def initialize_triggers(data_access: DataAccess):
    triggers = []

    condition = data_access
    new_trigger = Trigger()
    triggers.append(new_trigger)

    return triggers


class TriggerService:
    def __init__(self, data_access: DataAccess, telegram_service: TelegramService):
        self.triggers = initialize_triggers(data_access)

    def check_triggers(self, trigger_payload: TriggerPayload):
        for trigger in self.triggers:
            trigger.check(trigger_payload)
