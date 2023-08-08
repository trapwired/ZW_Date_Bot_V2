from typing import Callable

from Enums.PlayerState import PlayerState


class Transition(object):
    def __init__(self, action: Callable, new_state: PlayerState):
        self.new_state = new_state
        self.action = action
