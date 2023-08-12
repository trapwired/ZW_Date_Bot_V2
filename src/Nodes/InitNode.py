import configparser

import telegram
from telegram import Update, ChatMemberRestricted, ChatMemberMember, ChatMemberAdministrator, ChatMemberOwner

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from Exceptions.ObjectNotFoundException import ObjectNotFoundException

from Data.DataAccess import DataAccess

from Services.UserStateService import UserStateService
from Services.TelegramService import TelegramService

from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.UsersToState import UsersToState


def create_user(update: Update) -> TelegramUser:
    return TelegramUser(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)


class InitNode(Node):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, api_config: configparser.RawConfigParser, bot: telegram.Bot):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.group_chat_id = api_config['Telegram']['group_chat_id']
        self.bot = bot

    # Override to add new player
    async def handle(self, update: Update, user_to_state: UsersToState):
        telegram_id = update.effective_chat.id
        try:
            users_to_state = self.user_state_service.get_user_state(telegram_id)
        except ObjectNotFoundException:
            user = create_user(update)
            users_to_state = self.data_access.add(user)
        await super().handle(update, users_to_state)

    async def handle_start(self, update: Update, users_to_state: UsersToState):
        telegram_id = update.effective_chat.id
        if await self.is_in_group_chat(telegram_id):
            users_to_state = users_to_state.add_role(Role.PLAYER)
            self.user_state_service.update_user_state(users_to_state, UserState.DEFAULT)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)
        else:
            users_to_state = users_to_state.add_role(Role.REJECTED)
            self.user_state_service.update_user_state(users_to_state, UserState.REJECTED)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED)

    async def is_in_group_chat(self, telegram_id: int):
        chat_type = await self.bot.get_chat_member(self.group_chat_id, telegram_id)
        return type(chat_type) in [ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember, ChatMemberRestricted]

    async def handle_help(self, update: Update, user_to_state: UsersToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WRONG_START_COMMAND)
