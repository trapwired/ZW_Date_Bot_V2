from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService
from Data.DataAccess import DataAccess


class DefaultNode(Node):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, website_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.website_service = website_service

    async def handle_website(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        website = self.website_service.get_url()
        if not website:
            await self.telegram_service.send_message(
                update=update,
                all_buttons=None,
                message='The website link is not configured yet - an admin can set it via the admin menu.')
            return
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="handball.ch/Züri West 1", url=website)]])
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message_type=MessageType.WEBSITE,
            reply_markup=reply_markup)

    async def handle_privacy(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message_type=MessageType.PRIVACY)
