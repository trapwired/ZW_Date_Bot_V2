from abc import ABC, abstractmethod

from telegram import Update

from Enums.PlayerState import PlayerState
from Enums.MessageType import MessageType
from Services.TelegramService import TelegramService
from Data.DataAccess import DataAccess
from Services.PlayerStateService import PlayerStateService
from databaseEntities.PlayerToState import PlayerToState


class Node(ABC):

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, player_state_service: PlayerStateService, supports_string_commands: bool = False):
        super().__init__(telegram_service)
        self.data_access = data_access
        self.player_state_service = player_state_service
        self.supports_string_commands = supports_string_commands

    transitions = {}

    async def handle(self, update: Update, data_access: DataAccess, player_state: PlayerToState):
        try:
            action, newState = self.transitions[update.message.text]
            action(self, update, data_access, player_state)
            PlayerStateService.update_player_state(player_state, newState)
            
        except:
            self.telegram_service.send_message(update.effective_chat.id, MessageType.ERROR)

    @abstractmethod
    def action(self, update: Update, data_access: DataAccess, player_state: PlayerState):
        pass