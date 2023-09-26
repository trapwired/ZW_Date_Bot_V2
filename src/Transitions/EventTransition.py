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
                 additional_data_func: Callable = None,
                 is_active_function: partial = None):
        partial_func = partial(action, document_id=document_id, event_type=event_type)
        super().__init__(command=command, action=partial_func, allowed_roles=allowed_roles, new_state=new_state,
                         needs_description=needs_description, is_active_function=is_active_function)
        self.document_id = document_id
        self.additional_data_func = additional_data_func
        self.event_type = event_type

    def can_be_taken(self, command: str, role: Role) -> bool:
        return command.startswith(self.command) and self.is_for_role(role) and self.is_active()
