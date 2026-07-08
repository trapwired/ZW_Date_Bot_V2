from abc import ABC
from functools import partial
from typing import Callable

from telegram import Update

from Enums.UserState import UserState
from Enums import Audience
from domain.entities.UsersToState import UsersToState


def initialize_is_active_function(function):
    if function is not None:
        return function
    else:
        return lambda: True


class Transition(ABC):
    def __init__(self,
                 command: str,
                 action: Callable[[Update, UsersToState, UserState | None], None],
                 audience: Audience.Audience = Audience.EVERYONE,
                 new_state: UserState = None,
                 needs_description: bool = True,
                 is_active_function: partial = None,
                 in_keyboard: bool = True):
        self.command = command.lower()
        self.action = action
        self.audience = audience
        self.update_state = new_state is not None
        self.new_state = new_state
        self.needs_description = needs_description
        self.is_active_function = initialize_is_active_function(is_active_function)
        # Whether the command gets a button on the reply keyboard (aliases and
        # slash-command duplicates stay typeable but invisible).
        self.in_keyboard = in_keyboard

    def can_be_taken(self, command: str, user_to_state: UsersToState) -> bool:
        return self.command == command and self.is_for_user(user_to_state) and self.is_active()

    def is_for_user(self, user_to_state: UsersToState) -> bool:
        return self.audience.allows(user_to_state)

    def is_active(self):
        return self.is_active_function()
