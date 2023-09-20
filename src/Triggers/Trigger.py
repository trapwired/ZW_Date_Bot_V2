from abc import ABC
from typing import Callable

from Triggers.TriggerPayload import TriggerPayload


class Trigger(ABC):
    def __init__(self, pre_condition: Callable[[TriggerPayload], bool], condition: Callable[[TriggerPayload], bool],
                 notify_action: Callable[[TriggerPayload], None], message: str):
        self.pre_condition = pre_condition
        self.condition = condition
        self.notify_action = notify_action
        self.message = message

    def check(self, trigger_payload: TriggerPayload) -> bool:
        if not self.payload_is_valid(trigger_payload):
            return False
        if not self.pre_condition(trigger_payload):
            return False

        return self.condition(trigger_payload)

    def payload_is_valid(self, trigger_payload: TriggerPayload):
        return True
