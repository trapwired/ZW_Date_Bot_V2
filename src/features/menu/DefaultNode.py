from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from framework.Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService
from data.DataAccess import DataAccess

from features.adminpanel import AdminMenu
from features.events.EventsView import EventsView

from localization.Translator import t


class DefaultNode(Node):
    """The main menu - and, since the menu redesign, the only menu state. The reply
    keyboard's entries open inline menus (events, admin) or answer directly."""

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, website_service, events_view: EventsView, team_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.website_service = website_service
        self.events_view = events_view
        self.team_service = team_service

    async def handle_events(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        text, markup = self.events_view.build_list(user_to_state, update.effective_chat.id, None)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message=text,
            reply_markup=markup)

    async def handle_admin(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message=t(AdminMenu.PANEL_TEXT),
            reply_markup=AdminMenu.build_panel_markup())

    async def handle_website(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        website = self.website_service.get_url()
        if not website:
            await self.telegram_service.send_message(
                update=update,
                all_buttons=None,
                message=t('The website link is not configured yet - an admin can set it via the admin menu.'))
            return
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=self.team_service.current_team().name, url=website)]])
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
