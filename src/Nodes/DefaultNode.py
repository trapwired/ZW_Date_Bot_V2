from telegram import Update

from Nodes.Node import Node
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService


class DefaultNode(Node):

    async def handle(self, update: Update):
        pass
