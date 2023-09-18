from Triggers.Trigger import Trigger

from Triggers.TriggerPayload import TriggerPayload

from Enums.AttendanceState import AttendanceState


class AttendanceUpdateTrigger(Trigger):
    def check(self, trigger_payload: TriggerPayload):
        if not self.is_valid(trigger_payload):
            return
        if trigger_payload.new_attendance.state is not AttendanceState.NO:
            return


    # TODO rename is applicabale or something?
    def is_valid(self, trigger_payload: TriggerPayload):
        return not (trigger_payload.new_attendance is None
                    or trigger_payload.doc_id is None
                    or trigger_payload.event_type is None)
