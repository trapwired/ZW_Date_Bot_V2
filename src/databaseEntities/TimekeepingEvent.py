import datetime


class TimekeepingEvent:

    def __init__(self, timestamp: datetime, location: str, people_required: int = 2, doc_id: str = None):
        self.doc_id = doc_id
        self.timestamp = timestamp
        self.location = location
        self.people_required = people_required

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return TimekeepingEvent(source['timestamp'], source['location'], source['people_required'], doc_id)

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location,
                'people_required': self.people_required}

    def __repr__(self):
        return f"TimekeepingEvent(timestamp={self.timestamp}, location={self.location}, people_required={self.people_required}, doc_id={self.doc_id})"