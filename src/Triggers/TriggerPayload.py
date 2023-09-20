from databaseEntities.Attendance import Attendance

from Enums.Event import Event
from Enums.AttendanceState import AttendanceState


class TriggerPayload:
    def __init__(self, new_attendance: Attendance = None, doc_id: str = None, event_type: Event = None):
        self.new_attendance = new_attendance
        self.doc_id = doc_id
        self.event_type = event_type

    def attendance_is(self, attendance_state: AttendanceState) -> bool:
        return self.new_attendance.state == attendance_state

    def event_is(self, event_type: Event):
        return self.event_type == event_type
