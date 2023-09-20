from Triggers.Trigger import Trigger

from Triggers.TriggerPayload import TriggerPayload


class AttendanceUpdateTrigger(Trigger):

    def payload_is_valid(self, trigger_payload: TriggerPayload):
        return not (trigger_payload.new_attendance is None
                    or trigger_payload.doc_id is None
                    or trigger_payload.event_type is None)
