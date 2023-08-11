from Nodes.Node import Node
from telegram import Update

from Enums.MessageType import MessageType
from databaseEntities.PlayerToState import PlayerToState

from src.Data.DataAccess import DataAccess
from src.Enums.PlayerState import PlayerState
from src.Services.PlayerStateService import PlayerStateService
from src.Services.TelegramService import TelegramService


class RejectedNode(Node):

    def __init__(self, state: PlayerState, telegram_service: TelegramService, player_state_service: PlayerStateService,
                 data_access: DataAccess):
        super().__init__(state, telegram_service, player_state_service, data_access)
        self.transitions['/help'].update_state = False

    async def handle_correct_password(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME_SPECTATOR)

    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED,
                                                 'rejectedNode: handle_anything')
