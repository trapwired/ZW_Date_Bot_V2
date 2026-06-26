"""Application service for the role-assignment slice.

Owns the role data orchestration AdminNode and AssignRolesCallbackNode used to do
inline against DataAccess. Presentation (markup, display names) stays in the nodes.
"""
from Data.DataAccess import DataAccess

from Enums.Role import Role, ASSIGNABLE_ROLES
from Enums.UserState import UserState

from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.UsersToState import UsersToState


class RoleService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def role_counts(self) -> dict[Role, int]:
        return {role: self.data_access.get_role_user_count(role) for role in ASSIGNABLE_ROLES}

    def users_with_role(self, role: Role) -> list[tuple[str, TelegramUser]]:
        users_to_state = self.data_access.get_users_to_state_by_role(role)
        users = self.data_access.add_names([uts.user_id for uts in users_to_state])
        return [(uts.user_id, user) for uts, user in zip(users_to_state, users)]

    def get_user_and_state(self, user_doc_id: str) -> tuple[TelegramUser, UsersToState]:
        user = self.data_access.get_user_by_doc_id(user_doc_id)
        return user, self.data_access.get_user_state_for_user(user)

    def assign_role(self, user_doc_id: str, new_role: Role) -> TelegramUser:
        user, user_to_state = self.get_user_and_state(user_doc_id)
        user_to_state.add_role(new_role)
        # Their previous bot state may no longer be valid for the new role - send them back to the
        # main menu so the next interaction rebuilds the correct one.
        user_to_state.state = UserState.DEFAULT
        self.data_access.update(user_to_state)
        return user
