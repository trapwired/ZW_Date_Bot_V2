from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType

from databaseEntities.UsersToState import UsersToState


class DefaultNode(Node):

    async def handle_website(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WEBSITE,
                                                 'defaultNode: HandleWebsite')

    async def handle_stats(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.TO_STATS, 'defaultNode: Transition To stats')

    async def handle_edit(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.TO_EDIT, 'defaultNode: Transition to edit')

