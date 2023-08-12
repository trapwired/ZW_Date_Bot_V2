from typing import Callable

from telegram import Update

from Enums.UserState import UserState
from databaseEntities.UsersToState import UsersToState


class Transition(object):
    def __init__(self, action: Callable[[Update, UsersToState], None], new_state: UserState, update_state: bool = True):
        self.new_state = new_state
        self.action = action
        self.update_state = update_state
