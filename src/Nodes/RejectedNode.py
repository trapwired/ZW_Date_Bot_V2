from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from Nodes.Node import Node

from databaseEntities.UsersToState import UsersToState


class RejectedNode(Node):

    async def handle_correct_password(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        user_to_state = user_to_state.add_role(Role.SPECTATOR)
        self.data_access.update(user_to_state)
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.WELCOME)

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.REJECTED)
