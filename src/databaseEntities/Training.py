import datetime

from databaseEntities.DatabaseEntity import DatabaseEntity


class Training(DatabaseEntity):

    def __init__(self, timestamp: datetime, location: str, doc_id: str = None):
        super().__init__(doc_id)
        self.timestamp = timestamp
        self.location = location

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Training(source['timestamp'], source['location'], doc_id)

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location}

    def __repr__(self):
        return f"Training(timestamp={self.timestamp}, location={self.location}, doc_id={self.doc_id})"
