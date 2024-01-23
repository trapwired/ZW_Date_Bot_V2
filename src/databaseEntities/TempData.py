from datetime import datetime
import pandas as pd

from databaseEntities.DatabaseEntity import DatabaseEntity

from Utils import DateTimeUtils


class TempData(DatabaseEntity):

    def __init__(self, user_doc_id: str, timestamp: pd.Timestamp | str = None, location: str = None, opponent: str = None,
                 doc_id: str = None):
        super().__init__(doc_id)
        self.timestamp = DateTimeUtils.utc_to_zurich_timestamp(timestamp) if timestamp is not None else None
        self.location = location
        self.opponent = opponent
        self.user_doc_id = user_doc_id

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return TempData(source['userDocId'], source['timestamp'], source['location'], source['opponent'], doc_id)

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent,
                'userDocId': self.user_doc_id}

    def __repr__(self):
        return f"TempData(timestamp={self.timestamp}, location={self.location}, opponent={self.opponent}, user_doc_id={self.user_doc_id}, doc_id={self.doc_id})"
