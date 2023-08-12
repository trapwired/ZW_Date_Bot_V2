from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role

from Nodes.Node import Node

from databaseEntities.UsersToState import UsersToState


class RejectedNode(Node):

    async def handle_correct_password(self, update: Update, users_to_state: UsersToState):
        users_to_state = users_to_state.add_role(Role.SPECTATOR)
        self.data_access.update(users_to_state)
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)

    async def handle_help(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED)
