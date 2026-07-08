"""Application service for the role-assignment slice.

Owns the role data orchestration AdminNode and AssignRolesCallbackNode used to do
inline against DataAccess. Presentation (markup, display names) stays in the nodes.
"""
from data.DataAccess import DataAccess

from Enums.Role import Role, ASSIGNABLE_ROLES
from Enums.UserState import UserState

from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState

from Utils import PrintUtils


class RoleService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def role_counts(self) -> dict[Role, int]:
        return {role: self.data_access.get_role_user_count(role) for role in ASSIGNABLE_ROLES}

    def admin_count(self) -> int:
        return len(self.data_access.get_admins_to_state())

    def users_with_role(self, role: Role) -> list[tuple[UsersToState, TelegramUser]]:
        return self._with_users(self.data_access.get_users_to_state_by_role(role))

    def admins(self) -> list[tuple[UsersToState, TelegramUser]]:
        return self._with_users(self.data_access.get_admins_to_state())

    def _with_users(self, users_to_state: list[UsersToState]) -> list[tuple[UsersToState, TelegramUser]]:
        users = self.data_access.add_names([uts.user_id for uts in users_to_state])
        pairs = list(zip(users_to_state, users))
        return sorted(pairs, key=lambda pair: PrintUtils.get_player_display_name(pair[1]).lower())

    def get_user_and_state(self, user_doc_id: str) -> tuple[TelegramUser, UsersToState]:
        user = self.data_access.get_user_by_doc_id(user_doc_id)
        return user, self.data_access.get_user_state_for_user(user)

    def assign_role(self, user_doc_id: str, new_role: Role) -> tuple[TelegramUser, UsersToState]:
        user, user_to_state = self.get_user_and_state(user_doc_id)
        user_to_state.add_role(new_role)
        self._reset_to_main_menu(user_to_state)
        return user, user_to_state

    def toggle_admin(self, user_doc_id: str) -> tuple[TelegramUser, UsersToState]:
        """Flip the orthogonal admin flag; the membership role stays untouched."""
        user, user_to_state = self.get_user_and_state(user_doc_id)
        user_to_state.is_admin = not user_to_state.is_admin
        self._reset_to_main_menu(user_to_state)
        return user, user_to_state

    def _reset_to_main_menu(self, user_to_state: UsersToState) -> None:
        # Their previous bot state may no longer be valid for the new role/menus - send
        # them back to the main menu so the next interaction rebuilds the correct one.
        user_to_state.state = UserState.DEFAULT
        self.data_access.update(user_to_state)
