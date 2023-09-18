from abc import ABC

from Triggers.TriggerPayload import TriggerPayload


class Trigger(ABC):
    def __init__(self):
        # action_if_triggered

        # condition to check
        # i.e. more than
        pass

    def check(self, trigger_payload: TriggerPayload):
        pass

    def is_valid(self, trigger_payload: TriggerPayload):
        return True
