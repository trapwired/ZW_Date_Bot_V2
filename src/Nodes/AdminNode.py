from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.Role import ASSIGNABLE_ROLES

from databaseEntities.UsersToState import UsersToState

from Utils import CallbackUtils
from Utils import PrintUtils
from Utils import RoleAssignment


class AdminNode(Node):

    async def handle_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        all_statistics = self.data_access.get_user_to_player_metric()
        message = PrintUtils.pretty_print_statistics(all_statistics)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_STATISTICS,
            message=message)

    async def handle_game_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        game_statistics = self.data_access.get_attendance_statistics(Event.GAME)
        message = PrintUtils.pretty_print_event_statistics(game_statistics, Event.GAME)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_STATISTICS,
            message=message)

    async def handle_training_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        game_statistics = self.data_access.get_attendance_statistics(Event.TRAINING)
        message = PrintUtils.pretty_print_event_statistics(game_statistics, Event.TRAINING)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_STATISTICS,
            message=message)

    async def handle_timekeeping_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        game_statistics = self.data_access.get_attendance_statistics(Event.TIMEKEEPING)
        message = PrintUtils.pretty_print_event_statistics(game_statistics, Event.TIMEKEEPING)
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
        counts = {role: self.data_access.get_role_user_count(role) for role in ASSIGNABLE_ROLES}
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message='Select a role to manage:',
            reply_markup=RoleAssignment.build_overview_markup(counts))

    async def handle_update_website(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        current = self.data_access.get_website()
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
