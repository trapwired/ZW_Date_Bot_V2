import datetime


class Training:

    def __init__(self, timestamp: datetime, location: str):
        self.timestamp = timestamp
        self.location = location

    @staticmethod
    def from_dict(source: dict):
        return Training(source['timestamp'], source['location'])

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location}

    def __repr__(self):
        return f"Training(timestamp={self.timestamp}, location={self.location})"
