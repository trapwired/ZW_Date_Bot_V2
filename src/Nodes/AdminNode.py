from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils


class AdminNode(Node):

    async def handle_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        all_statistics = self.data_access.get_user_to_player_metric()
        message = PrintUtils.pretty_print_statistics(all_statistics)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message)

    async def handle_add(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)

    async def handle_update(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.UPDATE)
