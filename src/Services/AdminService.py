from Data import DataAccess

from Enums.Role import Role
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState


class AdminService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def set_user_inactive(self, chat_id: int):
        user_to_state = self.data_access.get_user_state(chat_id)
        user_to_state.add_role(Role.INACTIVE)
        self.data_access.update(user_to_state)
