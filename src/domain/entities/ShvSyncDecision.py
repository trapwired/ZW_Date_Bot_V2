import pandas as pd

from Enums.ShvSync import ShvDecisionKind, ShvDecisionStatus

from Utils import DateTimeUtils

from domain.entities.DatabaseEntity import DatabaseEntity


class ShvSyncDecision(DatabaseEntity):
    """One question the SHV sync asked the admins, keyed for the inline buttons by
    the short token (row uuids would blow Telegram's 64-byte callback_data budget)."""

    def __init__(self, token: str, kind: ShvDecisionKind, status: ShvDecisionStatus,
                 shv_game_id: int = None, game_doc_id: str = None, reason: str = None,
                 asked_at: pd.Timestamp = None, doc_id: str = None):
        super().__init__(doc_id)
        self.token = token
        self.kind = ShvDecisionKind(kind)
        self.status = ShvDecisionStatus(status)
        self.shv_game_id = int(shv_game_id) if shv_game_id is not None else None
        self.game_doc_id = game_doc_id
        self.reason = reason
        self.asked_at = DateTimeUtils.utc_to_zurich_timestamp(asked_at) if asked_at is not None else None

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return ShvSyncDecision(source['token'], source['kind'], source['status'],
                               source.get('shvGameId'), source.get('gameDocId'),
                               source.get('reason'), source.get('askedAt'), doc_id)

    def to_dict(self):
        return {'token': self.token,
                'kind': int(self.kind),
                'status': int(self.status),
                'shvGameId': self.shv_game_id,
                'gameDocId': self.game_doc_id,
                'reason': self.reason,
                'askedAt': self.asked_at}

    def __repr__(self):
        return (f"ShvSyncDecision(token={self.token}, kind={self.kind!r}, status={self.status!r}, "
                f"shv_game_id={self.shv_game_id}, game_doc_id={self.game_doc_id}, "
                f"reason={self.reason}, asked_at={self.asked_at}, doc_id={self.doc_id})")
