from typing import Callable

from Enums.PlayerState import PlayerState
from telegram import Update

from src.databaseEntities.PlayerToState import PlayerToState


class Transition(object):
    def __init__(self, action: Callable[[Update, PlayerToState], None], new_state: PlayerState):
        self.new_state = new_state
        self.action = action
