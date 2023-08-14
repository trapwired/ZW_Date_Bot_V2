from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState


class StatsNode(Node):

    async def handle_games(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_GAMES)

    async def handle_trainings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_TRAININGS)

    async def handle_timekeepings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_TIMEKEEPINGS)

    async def handle_document_id(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # Distinguish UsersToState
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_HANDLE_DOC_ID,
            message_extra_text='statsNode: handle_document_id')

    async def handle_overview(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # Distinguish UsersToState?
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_OVERVIEW)
