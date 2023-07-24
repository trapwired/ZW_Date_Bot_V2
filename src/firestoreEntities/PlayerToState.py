from src.States.AttendanceState import AttendanceState
from src.States.PlayerState import PlayerState


class PlayerToState:
    def __init__(self, player_id: str, state: PlayerState, additional_info: str = ''):
        self.player_id = player_id
        self.state = state
        self.additional_info = additional_info

    @staticmethod
    def from_dict(source):
        return PlayerToState(source['playerId'], source['state'], source['additionalInformation'])

    def to_dict(self):
        return {'playerId': self.player_id,
                'state': self.state,
                'additionalInformation': self.additional_info}

    def __repr__(self):
        return f"PlayerToState(playerId={self.player_id}, gameId={self.state}, state={self.additional_info})"
