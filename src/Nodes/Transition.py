from builtins import function

from Enums.PlayerState import PlayerState


class Transition(object):
    def __init__(self, action: function, new_state: PlayerState):
        self.new_state = new_state
        self.action = action
