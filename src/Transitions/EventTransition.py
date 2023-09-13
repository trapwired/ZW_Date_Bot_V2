from functools import partial

from Transitions.Transition import Transition
from typing import Callable

from telegram import Update

from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from Enums.Event import Event
from Enums.Role import Role

from databaseEntities.UsersToState import UsersToState


class EventTransition(Transition):
    def __init__(self,
                 command: str,
                 action: Callable[[Update, UsersToState, str, UserState | None], None],
                 document_id: str,
                 event_type: Event,
                 allowed_roles: RoleSet = RoleSet.EVERYONE,
                 new_state: UserState = None,
                 needs_description: bool = True,
                 additional_data_func: Callable = None):
        partial_func = partial(action, document_id=document_id, event_type=event_type)
        super().__init__(command, partial_func, allowed_roles, new_state, needs_description)
        self.document_id = document_id
        self.additional_data_func = additional_data_func
        self.event_type = event_type

    def can_be_taken(self, command: str, role: Role) -> bool:
        return command.startswith(self.command) and self.is_for_role(role) and self.is_active()
