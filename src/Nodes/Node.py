from abc import ABC, abstractmethod

from telegram import Update

from typing import Callable

from Services.TelegramService import TelegramService

from Services.PlayerStateService import PlayerStateService

from Data.DataAccess import DataAccess

from Enums.PlayerState import PlayerState
from Nodes.Transition import Transition
from databaseEntities.PlayerToState import PlayerToState

from Enums.MessageType import MessageType


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
        return self.transitions

    def add_transition(self, command: str, action: Callable, new_state: PlayerState = None):
        if new_state is None:
            new_state = self.state
        self.transitions[command] = Transition(action, new_state)

    def add_continue_later(self):
        self.add_transition('continue later', self.handle_continue_later, PlayerState.DEFAULT)

    async def handle(self, update: Update, player_to_state: PlayerToState):
        try:
            command = update.message.text
            transition = self.get_transition(command)
            action = transition.action
            await action(update, player_to_state)
            self.player_state_service.update_player_state(player_to_state, transition.new_state)

        except Exception as e:
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.ERROR, str(e))

    async def handle_unknown_command(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.UNKNOWN_COMMAND)
        pass  # TODO is it abstract, or already implemented here?

    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(
            update.effective_chat.id,
            MessageType.HELP,
            extra_text=str(type(self)),
            keyboard_btn_list=self.generate_keyboard())

    async def handle_continue_later(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.CONTINUE_LATER)
        pass  # TODO

    def generate_keyboard(self):
        # TODO via possible transitions (except help), generate keybaord + add to messages
        # add keyboard-gen as static class
        all_commands = list(self.transitions.keys())
        return [[x] for x in all_commands]

    def get_transition(self, command):
        transition = self.transitions.get(command)
        if transition is None:
            transition = self.transitions.get('/help')
        return transition
