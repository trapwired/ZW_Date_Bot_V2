from src.Data import DataAccess
from src.Enums.PlayerState import PlayerState


class PlayerStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_player_state(self, telegram_id: int):
        return self.data_access.get_player_state(telegram_id)
