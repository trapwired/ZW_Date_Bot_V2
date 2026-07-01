from telegram import Update

from framework.Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService
from Data.DataAccess import DataAccess

from Utils import CallbackUtils
from Utils import PrintUtils
from features.roles import RoleAssignment


class AdminNode(Node):

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, role_service, website_service, statistics_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.role_service = role_service
        self.website_service = website_service
        self.statistics_service = statistics_service

    async def handle_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        all_statistics = self.statistics_service.get_player_reminder_metrics()
        message = PrintUtils.pretty_print_statistics(all_statistics)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_STATISTICS,
            message=message)

    async def handle_game_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self._handle_event_statistics(Event.GAME, update, user_to_state, new_state)

    async def handle_training_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self._handle_event_statistics(Event.TRAINING, update, user_to_state, new_state)

    async def handle_timekeeping_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self._handle_event_statistics(Event.TIMEKEEPING, update, user_to_state, new_state)

    async def _handle_event_statistics(self, event_type: Event, update: Update, user_to_state: UsersToState,
                                       new_state: UserState):
        statistics = self.statistics_service.get_attendance_statistics(event_type)
        message = PrintUtils.pretty_print_event_statistics(statistics, event_type)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_STATISTICS,
            message=message)

    async def handle_reset_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message_type=MessageType.ADMIN_RESET_STATISTICS,
            reply_markup=CallbackUtils.get_reset_statistics_markup())

    async def handle_assign_roles(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        counts = self.role_service.role_counts()
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message='Select a role to manage:',
            reply_markup=RoleAssignment.build_overview_markup(counts))

    async def handle_update_website(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        current = self.website_service.get_url()
        current_text = current if current else 'not set'
        message = (f'The website link shown to players is currently:\n{current_text}\n\n'
                   'Send me the new URL, or /cancel to abort.')
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message)

    async def handle_add(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)

    async def handle_update(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.UPDATE)
