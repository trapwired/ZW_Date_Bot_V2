from telegram import Update

from Nodes.Node import Node

from src.Enums.MessageType import MessageType
from src.databaseEntities.UsersToState import UsersToState


class StatsNode(Node):

    async def handle_games(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_TO_GAMES,
                                                 'statsNode: HandleGames')

    async def handle_trainings(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_TO_TRAININGS, 'statsNode: HandleTrainings')

    async def handle_timekeepings(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_TO_TIMEKEEPINGS, 'statsNode: HandleTimekeepings')

    async def handle_document_id(self, update: Update, user_to_state: UsersToState):
        # TODO Distinguish UsersToState
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_HANDLE_DOC_ID, 'statsNode: handle_document_id')

    async def handle_overview(self, update: Update, user_to_state: UsersToState):
        # TODO Distinguish UsersToState
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_OVERVIEW, 'statsNode: handle_overview')




