from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from framework.Nodes.Node import Node

from domain.entities.UsersToState import UsersToState


class RejectedNode(Node):

    async def handle_correct_password(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # The role change is persisted by the framework's post-transition update_user_state
        # (this transition has update_state=True), so no explicit write is needed here.
        user_to_state = user_to_state.add_role(Role.SPECTATOR)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.WELCOME)

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.REJECTED)
