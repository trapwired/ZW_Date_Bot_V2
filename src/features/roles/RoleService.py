"""Application service for the role-assignment slice.

Owns the role data orchestration AdminNode and AssignRolesCallbackNode used to do
inline against DataAccess. Presentation (markup, display names) stays in the nodes.
"""
from data.DataAccess import DataAccess
from data.TenantContext import current_team_id

from Enums.Role import Role, ASSIGNABLE_ROLES
from Enums.UserState import UserState

from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState

from Utils import PrintUtils
from Utils.CustomExceptions import LastAdminException, RoleChangeTargetNotInTeamException


class RoleService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def overview_counts(self) -> tuple[dict[Role, int], int]:
        """Role-bucket sizes and the admin count, from ONE roster read."""
        members = self.data_access.get_users_to_state_by_team(current_team_id())
        counts = {role: sum(1 for m in members if m.role is role) for role in ASSIGNABLE_ROLES}
        return counts, sum(1 for m in members if m.is_admin)

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
        self._ensure_still_a_member(user_to_state)
        user_to_state.add_role(new_role)
        self._reset_to_main_menu(user_to_state)
        return user, user_to_state

    def toggle_admin(self, user_doc_id: str) -> tuple[TelegramUser, UsersToState]:
        """Flip the orthogonal admin flag; the membership role stays untouched."""
        user, user_to_state = self.get_user_and_state(user_doc_id)
        return user, self._set_admin(user_to_state, not user_to_state.is_admin)

    def grant_admin(self, user_doc_id: str) -> tuple[TelegramUser, UsersToState, bool]:
        """Idempotent grant (legacy 'make ADMIN' buttons): returns whether anything changed."""
        user, user_to_state = self.get_user_and_state(user_doc_id)
        if user_to_state.is_admin:
            return user, user_to_state, False
        return user, self._set_admin(user_to_state, True), True

    def _set_admin(self, user_to_state: UsersToState, is_admin: bool) -> UsersToState:
        self._ensure_still_a_member(user_to_state)
        if not is_admin and len(self.data_access.get_admins_to_state()) <= 1:
            # Zero admins = nobody can ever reach the admin menus again.
            raise LastAdminException()
        user_to_state.is_admin = is_admin
        self._reset_to_main_menu(user_to_state)
        return user_to_state

    def _ensure_still_a_member(self, user_to_state: UsersToState) -> None:
        # Buttons outlive rosters: a stale roles-menu message must not re-role (or
        # worse, re-admin) someone who has since left or been rejected.
        if not user_to_state.team_id or user_to_state.role in (Role.INIT, Role.REJECTED):
            raise RoleChangeTargetNotInTeamException()

    def _reset_to_main_menu(self, user_to_state: UsersToState) -> None:
        # Their previous bot state may no longer be valid for the new role/menus - send
        # them back to the main menu so the next interaction rebuilds the correct one.
        user_to_state.state = UserState.DEFAULT
        self.data_access.update(user_to_state)
