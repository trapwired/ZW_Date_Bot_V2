from telegram import Update

from Nodes.Node import Node
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService

from src.Enums.MessageType import MessageType
from src.databaseEntities.PlayerToState import PlayerToState


class StatsNode(Node):

    async def handle_games(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_TO_GAMES,
                                                 'statsNode: HandleGames')

    async def handle_trainings(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_TO_TRAININGS, 'statsNode: HandleTrainings')

    async def handle_timekeepings(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_TO_TIMEKEEPINGS, 'statsNode: HandleTimekeepings')

    async def handle_document_id(self, update: Update, player_to_state: PlayerToState):
        # TODO Distinguish PlayerToState
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_HANDLE_DOC_ID, 'statsNode: handle_document_id')

    async def handle_overview(self, update: Update, player_to_state: PlayerToState):
        # TODO Distinguish PlayerToState
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.STATS_OVERVIEW, 'statsNode: handle_overview')




