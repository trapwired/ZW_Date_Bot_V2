

from workflows.Workflow import Workflow
from Enums.PlayerState import PlayerState

class DomiWorkflow(Workflow):
    transitions = {PlayerState.FT {
        "/best", self.doSomething, PlayerState.DEFAULT
    }


    transitions = {
        "/best": [self.doSomething, PlayerState.DEFAULT],
        ...
    }

    }

    def handle(self, update, playerState):
        action, newState = transitions[playerState][update.command]
        action(update)
        updateState(newState)

    def doSomething(self, update):
        sendBotMEssage
        DoDatabaseThings
        pass