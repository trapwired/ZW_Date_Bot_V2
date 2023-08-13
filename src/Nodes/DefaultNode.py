from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState


class DefaultNode(Node):

    async def handle_website(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.WEBSITE,
            message_extra_text='defaultNode: HandleWebsite')

    async def handle_stats(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.TO_STATS,
            message_extra_text='defaultNode: Transition To stats')

    async def handle_edit(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.TO_EDIT,
            message_extra_text='defaultNode: Transition to edit')
