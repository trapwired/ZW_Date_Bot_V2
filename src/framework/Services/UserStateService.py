from data.DataAccess import DataAccess

from Enums.Role import Role
from Enums.UserState import UserState
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState


class UserStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_user_state(self, telegram_id: int):
        return self.data_access.get_user_state(telegram_id)

    def register_user(self, user: TelegramUser) -> UsersToState:
        return self.data_access.add(user)

    def update_user_state(self, user_to_state: UsersToState, new_state: UserState):
        user_to_state.state = new_state
        self.data_access.update(user_to_state)

    def bind_team_from_group_chat(self, user_to_state: UsersToState, group_chat_id) -> bool:
        """Stamp the team owning the given membership group chat (the tenant-binding
        seam, ADR 0001); False when no team is registered for that chat. The caller's
        subsequent full-document update persists the stamp."""
        team = self.data_access.find_team_by_group_chat(group_chat_id)
        if team is None:
            return False
        user_to_state.team_id = team.doc_id
        return True

    def set_user_inactive(self, chat_id: int):
        user_to_state = self.data_access.get_user_state(chat_id)
        user_to_state.add_role(Role.INACTIVE)
        self.data_access.update(user_to_state)
