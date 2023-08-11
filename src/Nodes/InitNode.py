from telegram import Update

from Nodes.Node import Node

from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService

from Enums.MessageType import MessageType

from databaseEntities.PlayerToState import PlayerToState

from Exceptions.ObjectNotFoundException import ObjectNotFoundException

from databaseEntities.Player import Player

from Enums.PlayerState import PlayerState

from Data.DataAccess import DataAccess


def create_player(update: Update) -> Player:
    return Player(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)


class InitNode(Node):

    def __init__(self, state: PlayerState, telegram_service: TelegramService, player_state_service: PlayerStateService,
                 data_access: DataAccess):
        super().__init__(state, telegram_service, player_state_service, data_access)
        self.transitions['/help'].update_state = False

    async def handle(self, update: Update, player_to_state: PlayerToState):
        try:
            telegram_id = update.effective_chat.id
            player_to_state = self.player_state_service.get_player_state(telegram_id)
        except ObjectNotFoundException:
            player = create_player(update)
            player_to_state = self.data_access.add(player)
        await super().handle(update, player_to_state)

    async def handle_start(self, update: Update, player_to_state: PlayerToState):
        # TODO authenticate
        telegram_id = update.effective_chat.id
        if self.is_allowed_to_use_bot(telegram_id):
            self.player_state_service.update_player_state(player_to_state, PlayerState.DEFAULT)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)
        else:
            self.player_state_service.update_player_state(player_to_state, PlayerState.REJECTED)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED)

    def is_allowed_to_use_bot(self, telegram_id: int):
        return False

    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WRONG_START_COMMAND,
                                                 'initNode: handle_help')
