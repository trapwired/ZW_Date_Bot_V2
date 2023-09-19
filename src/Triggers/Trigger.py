from abc import ABC
from typing import Callable

from Triggers.TriggerPayload import TriggerPayload


class Trigger(ABC):
    def __init__(self, check_condition: Callable[[TriggerPayload], bool], condition: Callable[[TriggerPayload], bool],
                 notify_action: Callable[[TriggerPayload], None]):
        self.check_condition = check_condition
        self.condition = condition
        self.notify_action = notify_action

    def check(self, trigger_payload: TriggerPayload):
        if not self.is_valid(trigger_payload):
            return
        if not self.check_condition(trigger_payload):
            return

        if self.condition(trigger_payload):
            self.notify_action(trigger_payload)

    def is_valid(self, trigger_payload: TriggerPayload):
        return True
