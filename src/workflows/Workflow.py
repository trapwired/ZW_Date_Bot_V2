from abc import ABC, abstractmethod

import telegram
from telegram import Update


class Workflow(ABC):

    def __init__(self, bot: telegram.Bot):
        self.bot = bot

    @abstractmethod
    def valid_commands(self):
        pass

    @abstractmethod
    def valid_states(self):
        pass

    @abstractmethod
    async def handle(self, update: Update):
        pass
