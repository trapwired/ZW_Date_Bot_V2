from src.Data import DataAccess
from src.Enums.PlayerState import PlayerState
from src.databaseEntities.Player import Player
from src.databaseEntities.PlayerToState import PlayerToState


class PlayerStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_player_state(self, telegram_id: int):
        return self.data_access.get_player_state(telegram_id)

    def update_player_state(self, player: Player, new_state: PlayerState):
        new_player_to_state = PlayerToState(player.doc_id, new_state)
        self.data_access.update(new_player_to_state)
