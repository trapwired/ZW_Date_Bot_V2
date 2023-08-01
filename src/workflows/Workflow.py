from abc import ABC, abstractmethod

import telegram
from telegram import Update

from src.Enums.PlayerState import PlayerState
from src.Services.TelegramService import TelegramService


class Workflow(ABC):

    def __init__(self, telegram_service: TelegramService, supports_string_commands: bool = False):
        self.telegram_service = telegram_service
        self.supports_string_commands = supports_string_commands

    @abstractmethod
    def valid_commands(self):
        pass

    @abstractmethod
    def valid_states(self):
        pass

    @abstractmethod
    async def handle(self, update: Update, player_state: PlayerState):
        pass
