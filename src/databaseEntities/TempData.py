import pandas as pd

from databaseEntities.DatabaseEntity import DatabaseEntity

from Utils import DateTimeUtils

from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.Game import Game
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training


# Ordered fields the add-event wizard collects per event type (games also collect an
# opponent). Single source of truth for both the wizard's step traversal
# (AddEventFieldsNode) and TempData.infer_step, so the two can't drift.
FIELD_ORDER = {
    Event.GAME: (CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.OPPONENT),
    Event.TRAINING: (CallbackOption.DATETIME, CallbackOption.LOCATION),
    Event.TIMEKEEPING: (CallbackOption.DATETIME, CallbackOption.LOCATION),
}


class TempData(DatabaseEntity):

    def __init__(self, user_doc_id: str, event_type: Event, timestamp: pd.Timestamp | str = None, location: str = None,
                 opponent: str = None, chat_id: int = None, query_id: int = None,
                 step: CallbackOption | str | int = CallbackOption.DATETIME, doc_id: str = None):
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
        # The add-event wizard step: which field this draft is currently collecting
        # (DATETIME -> LOCATION -> [OPPONENT] -> SAVE). Held here instead of in UserState.
        if type(step) is str or type(step) is int:
            step = CallbackOption(int(step))
        self.step = step

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        temp_data = TempData(source['userDocId'], source['eventType'], source['timestamp'], source['location'],
                             source['opponent'], source['chatId'], source['queryId'], doc_id=doc_id)
        stored_step = source.get('step')
        # Legacy drafts (created before TempData.step existed) have no persisted step;
        # infer it from which fields are already filled so an in-flight wizard resumes
        # where it left off instead of restarting at the timestamp prompt.
        temp_data.step = CallbackOption(int(stored_step)) if stored_step is not None else temp_data.infer_step()
        return temp_data

    def infer_step(self) -> CallbackOption:
        """The wizard step implied by which fields are already collected: the first
        field in the collection order that is still empty, or SAVE once all are set."""
        collected = {CallbackOption.DATETIME: self.timestamp,
                     CallbackOption.LOCATION: self.location,
                     CallbackOption.OPPONENT: self.opponent}
        for step in FIELD_ORDER[self.event_type]:
            if collected[step] is None:
                return step
        return CallbackOption.SAVE

    def to_dict(self):
        return {'userDocId': self.user_doc_id,
                'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent,
                'chatId': self.chat_id,
                'queryId': self.query_id,
                'step': self.step,
                'eventType': self.event_type}

    def __repr__(self):
        return (f"TempData(userDocId={self.user_doc_id}, timestamp={self.timestamp}, location={self.location}, "
                f"opponent={self.opponent}, chatId={self.chat_id}, queryId={self.query_id}, step={self.step}, "
                f"eventType={self.event_type}, doc_id={self.doc_id})")

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
