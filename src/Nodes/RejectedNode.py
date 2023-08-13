from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role

from Nodes.Node import Node

from databaseEntities.UsersToState import UsersToState


class RejectedNode(Node):

    async def handle_correct_password(self, update: Update, user_to_state: UsersToState):
        user_to_state = user_to_state.add_role(Role.SPECTATOR)
        self.data_access.update(user_to_state)
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.WELCOME)

    async def handle_help(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.REJECTED)
