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

    def join_team(self, user_to_state: UsersToState, team_id: str, role: Role,
                  new_state: UserState = UserState.DEFAULT, is_admin: bool = False) -> None:
        """THE seam that attaches a user to a team (ADR 0001): team, role, admin flag and
        state land in one persisted write, so no onboarding path can stamp one without the
        others. An existing admin bit survives a re-join (a healed admin re-/starting must
        not be demoted); it is only ever cleared by leave_team or the roles menu."""
        user_to_state.add_role(role)
        user_to_state.is_admin = is_admin or user_to_state.is_admin
        user_to_state.team_id = team_id
        user_to_state.state = new_state
        self.data_access.update(user_to_state)

    def leave_team(self, user_to_state: UsersToState) -> None:
        """Undo join_team in one persisted write: back to the teamless INIT stance
        (used when an aborted team setup is rolled back)."""
        user_to_state.add_role(Role.INIT)
        user_to_state.is_admin = False
        user_to_state.team_id = None
        user_to_state.state = UserState.INIT
        self.data_access.update(user_to_state)

    def reject(self, user_to_state: UsersToState) -> None:
        """Park a user in the REJECTED stance in one persisted write. Clearing the
        admin bit lives HERE so no rejection path can leave the admin menus reachable
        (Audience.ADMINS gates purely on the flag)."""
        user_to_state.add_role(Role.REJECTED)
        user_to_state.is_admin = False
        user_to_state.state = UserState.REJECTED
        self.data_access.update(user_to_state)

    def set_language(self, user_to_state: UsersToState, language: str) -> None:
        user_to_state.language = language
        self.data_access.update(user_to_state)

    def set_user_inactive(self, chat_id: int):
        user_to_state = self.data_access.get_user_state(chat_id)
        user_to_state.add_role(Role.INACTIVE)
        self.data_access.update(user_to_state)
