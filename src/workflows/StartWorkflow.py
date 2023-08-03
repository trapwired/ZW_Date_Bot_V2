from telegram import Update

from src.Data.DataAccess import DataAccess
from src.Enums.MessageType import MessageType
from src.Enums.PlayerState import PlayerState
from src.Services.PlayerStateService import PlayerStateService
from src.Services.TelegramService import TelegramService
from src.databaseEntities.Player import Player
from src.workflows.Workflow import Workflow


def create_player(update: Update) -> Player:
    return Player(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)


class StartWorkflow(Workflow):

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess,
                 player_state_service: PlayerStateService):
        super().__init__(telegram_service)
        self.data_access = data_access
        self.player_state_service = player_state_service

    async def handle(self, update: Update, player_state: PlayerState):
        # player is not present
        command = update.message.text.lower()
        telegram_id = update.effective_chat.id
        if not command == '/start':
            await self.telegram_service.send_message(telegram_id, MessageType.WRONG_START_COMMAND)
            return
        player = create_player(update)
        new_player = self.data_access.add(player)
        await self.telegram_service.send_message(telegram_id, MessageType.WELCOME)
        self.player_state_service.update_player_state(new_player, PlayerState.MAIN_MENU)
        await self.telegram_service.send_message(telegram_id, MessageType.HELP)

    def valid_commands(self):
        return []

    def valid_states(self):
        return []
