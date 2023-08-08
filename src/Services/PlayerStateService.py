from Data import DataAccess
from Enums.PlayerState import PlayerState
from databaseEntities.PlayerToState import PlayerToState


class PlayerStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_player_state(self, telegram_id: int):
        return self.data_access.get_player_state(telegram_id)

    def update_player_state(self, player_to_state: PlayerToState, new_state: PlayerState):
        player_to_state.state = new_state
        self.data_access.update(player_to_state)
