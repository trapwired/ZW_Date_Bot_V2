from telegram import Update

from Nodes.Node import Node
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService

from databaseEntities.PlayerToState import PlayerToState

from Enums.MessageType import MessageType


class DefaultNode(Node):

    async def handle_website(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WEBSITE,
                                                 'defaultNode: HandleWebsite')

    async def handle_stats(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.TO_STATS, 'defaultNode: Transition To stats')

    async def handle_edit(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.TO_EDIT, 'defaultNode: Transition to edit')

