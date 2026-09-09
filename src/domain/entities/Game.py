import pandas as pd

from Utils import DateTimeUtils
from domain.entities.DatabaseEntity import DatabaseEntity


class Game(DatabaseEntity):

    def __init__(self, timestamp: pd.Timestamp | str, location: str, opponent: str,
                 shv_game_id: int = None, doc_id: str = None):
        super().__init__(doc_id)
        self.timestamp = DateTimeUtils.utc_to_zurich_timestamp(timestamp)
        self.location = location
        self.opponent = opponent
        # SHV matchcenter objectId for API-synced games; None for manually added ones.
        self.shv_game_id = int(shv_game_id) if shv_game_id is not None else None

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Game(source['timestamp'], source['location'], source['opponent'],
                    source.get('shvGameId'), doc_id)

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent,
                'shvGameId': self.shv_game_id}

    def __repr__(self):
        return f"Game(timestamp={self.timestamp}, location={self.location}, opponent={self.opponent}, shv_game_id={self.shv_game_id}, doc_id={self.doc_id})"
