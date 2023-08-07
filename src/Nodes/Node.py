from abc import ABC, abstractmethod
from builtins import function

from telegram import Update

from Services.TelegramService import TelegramService

from Services.PlayerStateService import PlayerStateService

from Data.DataAccess import DataAccess

from src.Enums.PlayerState import PlayerState
from src.Nodes.Transition import Transition


class Node(ABC):

    def __init__(self, state: PlayerState, telegram_service: TelegramService, player_state_service: PlayerStateService,
                 data_access: DataAccess):
        self.state = state
        self.data_access = data_access
        self.player_state_service = player_state_service
        self.telegram_service = telegram_service
        self.transitions = dict()
        self.add_transition('', self.handle_unknown_command)  # TODO handle unknown command, clever regex?
        self.add_transition('/help', self.handle_help)

    def transitions(self) -> dict:
        return self.transitions.

    def add_transition(self, command: str, action: function, new_state: PlayerState = None):
        if new_state is None:
            new_state = self.state
        self.transitions[command] = Transition(action, new_state)

    def add_continue_later(self):
        self.add_transition('continue later', self.handle_continue_later, PlayerState.DEFAULT)

    async def handle(self, update: Update):
        try:
            command = update.message.text
            transition = self.transitions.get(command) # TODO maybe overwrite
            # TODO do something with transition
            action(self, update, data_access, player_state)
            PlayerStateService.update_player_state(player_state, newState)

        except:
            self.telegram_service.send_message(update.effective_chat.id, MessageType.ERROR)

    @abstractmethod
    async def handle_unknown_command(self, update: Update):
        pass  # is it abstract, or already implemented here?

    async def handle_help(self, update: Update):
        pass  # TODO generate and send help (all transitions possible)

    async def handle_continue_later(self, update: Update):
        pass # TODO

    def generate_keyboard(self):
        # TODO via possible transitions (except help), generate keybaord + add to messages
        # add keyboard-gen as static class
        pass