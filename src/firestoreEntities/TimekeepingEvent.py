import datetime


class TimekeepingEvent:

    def __init__(self, timestamp: datetime, location: str, people_required: int):
        self.timestamp = timestamp
        self.location = location
        self.people_required = people_required

    @staticmethod
    def from_dict(source):
        return TimekeepingEvent(source['timestamp'], source['location'], source['people_required'])

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location,
                'people_required': self.people_required}

    def __repr__(self):
        return f"Game(timestamp={self.timestamp}, location={self.location}, people_required={self.people_required})"
