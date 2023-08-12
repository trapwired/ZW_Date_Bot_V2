from Data import DataAccess

from Enums.UserState import UserState
from databaseEntities.UsersToState import UsersToState


class UserStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_user_state(self, telegram_id: int):
        return self.data_access.get_user_state(telegram_id)

    def update_user_state(self, user_to_state: UsersToState, new_state: UserState):
        user_to_state.state = new_state
        self.data_access.update(user_to_state)
