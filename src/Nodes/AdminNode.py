from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils


class AdminNode(Node):

    async def handle_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        all_statistics = self.data_access.get_user_to_player_metric()
        message = PrintUtils.pretty_print_statistics(all_statistics)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message)

    async def handle_game_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        game_statistics = self.data_access.get_attendance_statistics(Event.GAME)
        message = PrintUtils.pretty_print_event_statistics(game_statistics, Event.GAME)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message)

    async def handle_training_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        game_statistics = self.data_access.get_attendance_statistics(Event.TRAINING)
        message = PrintUtils.pretty_print_event_statistics(game_statistics, Event.TRAINING)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message)

    async def handle_timekeeping_statistics(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        game_statistics = self.data_access.get_attendance_statistics(Event.TIMEKEEPING)
        message = PrintUtils.pretty_print_event_statistics(game_statistics, Event.TIMEKEEPING)
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
