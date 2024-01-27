import pandas as pd

from databaseEntities.DatabaseEntity import DatabaseEntity

from Utils import DateTimeUtils

from Enums.Event import Event

from databaseEntities.Game import Game
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training


class TempData(DatabaseEntity):

    def __init__(self, user_doc_id: str, event_type: Event, timestamp: pd.Timestamp | str = None, location: str = None,
                 opponent: str = None, chat_id: int = None, query_id: int = None, doc_id: str = None):
        super().__init__(doc_id)
        self.user_doc_id = user_doc_id
        self.timestamp = DateTimeUtils.utc_to_zurich_timestamp(timestamp) if timestamp is not None else None
        self.location = location
        self.opponent = opponent
        self.chat_id = int(chat_id) if chat_id else None
        self.query_id = int(query_id) if query_id else None
        if type(event_type) is str or type(event_type) is int:
            event_type = Event(int(event_type))
        self.event_type = event_type

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return TempData(source['userDocId'], source['eventType'], source['timestamp'], source['location'],
                        source['opponent'], source['chatId'], source['queryId'], doc_id)

    def to_dict(self):
        return {'userDocId': self.user_doc_id,
                'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent,
                'chatId': self.chat_id,
                'queryId': self.query_id,
                'eventType': self.event_type}

    def __repr__(self):
        return (f"TempData(userDocId={self.user_doc_id}, timestamp={self.timestamp}, location={self.location}, "
                f"opponent={self.opponent}, chatId={self.chat_id}, queryId={self.query_id}, eventType={self.event_type},"
                f" doc_id={self.doc_id})")

    def get_finished_event(self):
        match self.event_type:
            case Event.GAME:
                return Game(self.timestamp, self.location, self.opponent)
            case Event.TRAINING:
                return Training(self.timestamp, self.location)
            case Event.TIMEKEEPING:
                return TimekeepingEvent(self.timestamp, self.location)

    def add_inline_information(self, chat_id: int, query_id: int):
        self.chat_id = int(chat_id)
        self.query_id = int(query_id)
        return self
