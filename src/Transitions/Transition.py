import logging
from abc import ABC
from typing import Callable

from telegram import Update

from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from databaseEntities.UsersToState import UsersToState

from Enums.Role import Role


class Transition(ABC):
    def __init__(self,
                 command: str,
                 action: Callable[[Update, UsersToState, UserState | None], None],
                 allowed_roles: RoleSet = RoleSet.EVERYONE,
                 new_state: UserState = None,
                 needs_description: bool = True):
        self.command = command.lower()
        self.action = action
        self.allowed_roles = allowed_roles
        self.update_state = new_state is not None
        self.new_state = new_state
        self.needs_description = needs_description

    def can_be_taken(self, command: str, role: Role) -> bool:
        return self.command == command and self.is_for_role(role)

    def is_for_role(self, role: Role) -> bool:
        return role in self.allowed_roles
