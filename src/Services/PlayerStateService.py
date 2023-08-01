from src.Data import DataAccess
from src.Enums.PlayerState import PlayerState


class PlayerStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_player_state(self, telegram_id: int):
        # return data_Acces.get_player_State
        return PlayerState.INIT
