from functools import partial

from Transitions.Transition import Transition
from typing import Callable

from telegram import Update

from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from Enums.Event import Event


from databaseEntities.UsersToState import UsersToState


class EventTransition(Transition):
    def __init__(self,
                 command: str,
                 action: Callable[[Update, UsersToState, str, UserState | None], None],
                 document_id: str,
                 event_type: Event,
                 allowed_roles: RoleSet = RoleSet.EVERYONE,
                 new_state: UserState = None,
                 needs_description: bool = True):
        partial_func = partial(action, document_id=document_id, event_type=event_type)
        super().__init__(command, partial_func, allowed_roles, new_state, needs_description)
        self.document_id = document_id
