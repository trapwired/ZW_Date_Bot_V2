from Enums.Event import Event
from databaseEntities.Attendance import Attendance


class TriggerPayload:
    def __init__(self, new_attendance: Attendance = None, doc_id: str = None, event_type: Event = None):
        self.new_attendance = new_attendance
        self.doc_id = doc_id
        self.event_type = event_type