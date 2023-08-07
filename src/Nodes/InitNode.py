from telegram import Update

from Nodes.Node import Node
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService


class InitNode(Node):

    async def handle(self, update: Update):
        pass

    async def handle_start(self, update: Update):
        pass

    async def handle_else(self, update: Update):
        pass
