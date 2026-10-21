from datetime import datetime

from Utils import DateTimeUtils

from domain.entities.DatabaseEntity import DatabaseEntity


class CalendarToken(DatabaseEntity):
    """A user's one live calendar-feed link. Only the sha256 hash of the token is
    stored; the raw token exists once, in the link shown to the user."""

    def __init__(self, token_hash: str, user_id: str, created_at: datetime,
                 last_used_at: datetime | None = None, doc_id: str = None):
        super().__init__(doc_id)
        self.token_hash = token_hash
        self.user_id = user_id
        self.created_at = DateTimeUtils.utc_to_zurich_timestamp(created_at)
        self.last_used_at = (DateTimeUtils.utc_to_zurich_timestamp(last_used_at)
                             if last_used_at is not None else None)

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return CalendarToken(source['tokenHash'], source['userId'], source['createdAt'],
                             source.get('lastUsedAt'), doc_id)

    def to_dict(self):
        return {'tokenHash': self.token_hash,
                'userId': self.user_id,
                'createdAt': self.created_at,
                'lastUsedAt': self.last_used_at}

    def __repr__(self):
        # token_hash is left out on purpose: credential material stays out of logs.
        return (f"CalendarToken(user_id={self.user_id}, created_at={self.created_at}, "
                f"last_used_at={self.last_used_at}, doc_id={self.doc_id})")
