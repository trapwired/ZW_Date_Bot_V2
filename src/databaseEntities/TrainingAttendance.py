from Enums.AttendanceState import AttendanceState


class TrainingAttendance(object):
    def __init__(self, user_id: str, game_id: str, state: AttendanceState, doc_id: str = None):
        self.doc_id = doc_id
        self.user_id = user_id
        self.game_id = game_id
        self.state = state

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return TrainingAttendance(source['userId'], source['gameId'], source['state'], doc_id)

    def add_document_id(self, doc_id: str):
        self.doc_id = doc_id
        return self

    def to_dict(self):
        return {'userId': self.user_id,
                'gameId': self.game_id,
                'state': self.state}

    def __repr__(self):
        return f"TrainingAttendance(userId={self.user_id}, gameId={self.game_id}, state={self.state}, doc_id={self.doc_id})"
