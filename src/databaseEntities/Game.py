import pandas as pd

from Utils import DateTimeUtils
from databaseEntities.DatabaseEntity import DatabaseEntity


class Game(DatabaseEntity):

    def __init__(self, timestamp: pd.Timestamp | str, location: str, opponent: str, doc_id: str = None):
        super().__init__(doc_id)
        self.timestamp = DateTimeUtils.utc_to_zurich_timestamp(timestamp)
        self.location = location
        self.opponent = opponent

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Game(source['timestamp'], source['location'], source['opponent'], doc_id)

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent}

    def __repr__(self):
        return f"Game(timestamp={self.timestamp}, location={self.location}, opponent={self.opponent}, doc_id={self.doc_id})"
