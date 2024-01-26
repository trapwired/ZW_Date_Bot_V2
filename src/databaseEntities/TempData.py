from datetime import datetime
import pandas as pd

from databaseEntities.DatabaseEntity import DatabaseEntity

from Utils import DateTimeUtils


class TempData(DatabaseEntity):

    def __init__(self, user_doc_id: str, timestamp: pd.Timestamp | str = None, location: str = None,
                 opponent: str = None, chat_id: int = None, query_id: int = None, doc_id: str = None):
        super().__init__(doc_id)
        self.user_doc_id = user_doc_id
        self.timestamp = DateTimeUtils.utc_to_zurich_timestamp(timestamp) if timestamp is not None else None
        self.location = location
        self.opponent = opponent
        self.chat_id = int(chat_id) if chat_id else None
        self.query_id = int(query_id) if query_id else None

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return TempData(source['userDocId'], source['timestamp'], source['location'], source['opponent'],
                        source['chatId'], source['queryId'], doc_id)

    def to_dict(self):
        return {'userDocId': self.user_doc_id,
                'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent,
                'chatId': self.chat_id,
                'queryId': self.query_id}

    def __repr__(self):
        return (f"TempData(userDocId={self.user_doc_id}, timestamp={self.timestamp}, location={self.location}, "
                f"opponent={self.opponent}, chatId={self.chat_id}, queryId={self.query_id}, doc_id={self.doc_id})")

    def get_game_parameters(self):
        return self.timestamp, self.location, self.opponent

    def add_inline_information(self, chat_id: int, query_id: int):
        self.chat_id = int(chat_id)
        self.query_id = int(query_id)
        return self
