from telegram import Update

from Nodes.Node import Node
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService

from Enums.MessageType import MessageType

from databaseEntities.PlayerToState import PlayerToState


class InitNode(Node):

    async def handle_start(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)

    async def handle_else(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WRONG_START_COMMAND, 'initNode: handle_else')
