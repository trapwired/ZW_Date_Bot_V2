import configparser

import telegram
from telegram import Update, ChatMemberRestricted, ChatMemberMember, ChatMemberAdministrator, ChatMemberOwner

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.PlayerState import PlayerState
from Enums.Role import Role

from databaseEntities.PlayerToState import PlayerToState
from databaseEntities.Player import Player

from Exceptions.ObjectNotFoundException import ObjectNotFoundException

from src.Data.DataAccess import DataAccess
from src.Services.PlayerStateService import PlayerStateService
from src.Services.TelegramService import TelegramService


def create_player(update: Update) -> Player:
    return Player(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)


class InitNode(Node):

    def __init__(self, state: PlayerState, telegram_service: TelegramService, player_state_service: PlayerStateService,
                 data_access: DataAccess, api_config: configparser.RawConfigParser, bot: telegram.Bot):
        super().__init__(state, telegram_service, player_state_service, data_access)
        self.group_chat_id = api_config['Telegram']['group_chat_id']
        self.bot = bot

    # Override to add new player
    async def handle(self, update: Update, player_to_state: PlayerToState):
        telegram_id = update.effective_chat.id
        try:
            player_to_state = self.player_state_service.get_player_state(telegram_id)
        except ObjectNotFoundException:
            player = create_player(update)
            player_to_state = self.data_access.add(player)
        await super().handle(update, player_to_state)

    async def handle_start(self, update: Update, player_to_state: PlayerToState):
        telegram_id = update.effective_chat.id
        if await self.is_in_group_chat(telegram_id):
            player_to_state = player_to_state.add_role(Role.PLAYER)
            self.player_state_service.update_player_state(player_to_state, PlayerState.DEFAULT)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)
        else:
            player_to_state = player_to_state.add_role(Role.REJECTED)
            self.player_state_service.update_player_state(player_to_state, PlayerState.REJECTED)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED)

    async def is_in_group_chat(self, telegram_id: int):
        chat_type = await self.bot.get_chat_member(self.group_chat_id, telegram_id)
        return type(chat_type) in [ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember, ChatMemberRestricted]

    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WRONG_START_COMMAND)
