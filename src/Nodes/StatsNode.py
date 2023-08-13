from telegram import Update

from Nodes.Node import Node

from src.Enums.MessageType import MessageType
from src.databaseEntities.UsersToState import UsersToState


class StatsNode(Node):

    async def handle_games(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.STATS_TO_GAMES,
            message_extra_text='statsNode: HandleGames')

    async def handle_trainings(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.STATS_TO_TRAININGS,
            message_extra_text='statsNode: HandleTrainings')

    async def handle_timekeepings(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.STATS_TO_TIMEKEEPINGS,
            message_extra_text='statsNode: HandleTimekeepings')

    async def handle_document_id(self, update: Update, user_to_state: UsersToState):
        # Distinguish UsersToState
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.STATS_HANDLE_DOC_ID,
            message_extra_text='statsNode: handle_document_id')

    async def handle_overview(self, update: Update, user_to_state: UsersToState):
        # Distinguish UsersToState?
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role),
            message_type=MessageType.STATS_OVERVIEW,
            message_extra_text='statsNode: handle_overview')
