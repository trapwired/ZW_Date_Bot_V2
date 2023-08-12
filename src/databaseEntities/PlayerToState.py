from Enums.PlayerState import PlayerState
from Enums.Role import Role


class PlayerToState(object):
    def __init__(self, player_id: str, state: PlayerState, additional_info: str = '', doc_id: str = None,
                 role: Role = Role.INIT):
        self.doc_id = doc_id
        self.player_id = player_id
        self.state = state
        self.additional_info = additional_info
        self.role = role

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return PlayerToState(
            source['playerId'],
            source['state'],
            source['additionalInformation'],
            doc_id,
            source['role'])

    def add_role(self, role: Role):
        self.role = role
        return self

    def add_document_id(self, doc_id: str):
        self.doc_id = doc_id
        return self

    def to_dict(self):
        return {'playerId': self.player_id,
                'state': self.state,
                'additionalInformation': self.additional_info,
                'role': self.role}

    def __repr__(self):
        return f"PlayerToState(playerId={self.player_id}, gameId={self.state}, state={self.additional_info}, doc_id={self.doc_id}, role={self.role})"
