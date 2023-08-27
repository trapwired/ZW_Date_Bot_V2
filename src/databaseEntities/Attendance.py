from Enums.AttendanceState import AttendanceState


class Attendance(object):
    def __init__(self, user_id: str, event_id: str, state: AttendanceState | str, doc_id: str = None):
        self.doc_id = doc_id
        self.user_id = user_id
        self.event_id = event_id
        if type(state) is str:
            state = AttendanceState(int(state))
        self.state = state

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Attendance(source['userId'], source['eventId'], source['state'], doc_id)

    def add_document_id(self, doc_id: str):
        self.doc_id = doc_id
        return self

    def to_dict(self):
        return {'userId': self.user_id,
                'eventId': self.event_id,
                'state': self.state}

    def __repr__(self):
        return f"GameAttendance(userId={self.user_id}, eventId={self.event_id}, state={self.state}, doc_id={self.doc_id})"
