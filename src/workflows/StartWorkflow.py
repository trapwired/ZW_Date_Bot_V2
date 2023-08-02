from telegram import Update

from src.Data.DataAccess import DataAccess
from src.Enums.MessageType import MessageType
from src.Enums.PlayerState import PlayerState
from src.Services.TelegramService import TelegramService
from src.databaseEntities.Player import Player
from src.workflows.Workflow import Workflow


class StartWorkflow(Workflow):

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess):
        super().__init__(telegram_service)
        self.data_access = data_access

    async def handle(self, update: Update, player_state: PlayerState):
        # player is not present
        command = update.message.text.lower()
        telegram_id = update.effective_chat.id
        if not command == '/start':
            await self.telegram_service.send_message(telegram_id, MessageType.WRONG_START_COMMAND)
            return
        player = self.create_player(update)
        self.data_access.add(player)
        await self.telegram_service.send_message(telegram_id, MessageType.WELCOME)
        # TODO send help or default keys

    def valid_commands(self):
        return []

    def valid_states(self):
        return []

    def create_player(self, update: Update) -> Player:
        return Player(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)