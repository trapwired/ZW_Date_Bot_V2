from src.States.AttendanceState import AttendanceState


class PlayerToGame:
    def __init__(self, player_id: str, game_id: str, state: AttendanceState):
        self.player_id = player_id
        self.game_id = game_id
        self.state = state

    @staticmethod
    def from_dict(source):
        return PlayerToGame(source['playerId'], source['gameId'], source['state'])

    def to_dict(self):
        return {'playerId': self.player_id,
                'gameId': self.game_id,
                'state': self.state}

    def __repr__(self):
        return f"PlayerToGame(playerId={self.player_id}, gameId={self.game_id}, state={self.state})"
