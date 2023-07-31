from abc import ABC, abstractmethod

import telegram
from telegram import Update

from src.Services.TelegramService import TelegramService


class Workflow(ABC):

    def __init__(self, telegram_service: TelegramService):
        self.telegram_service = telegram_service

    @abstractmethod
    def valid_commands(self):
        pass

    @abstractmethod
    def valid_states(self):
        pass

    @abstractmethod
    async def handle(self, update: Update):
        pass
