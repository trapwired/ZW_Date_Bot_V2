from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils
from Utils import CallbackUtils


class EditNode(Node):

    async def handle_game_id(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                              document_id: str, event_type: Event):
        game = self.data_access.get_game(document_id)
        message = PrintUtils.pretty_print(game)
        reply_markup = CallbackUtils.get_reply_markup(UserState.EDIT, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message,
            reply_markup=reply_markup)

    async def handle_training_id(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                              document_id: str, event_type: Event):
        training = self.data_access.get_training(document_id)
        message = PrintUtils.pretty_print(training)
        reply_markup = CallbackUtils.get_reply_markup(UserState.EDIT, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message,
            reply_markup=reply_markup)

    async def handle_timekeeping_id(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                              document_id: str, event_type: Event):
        training = self.data_access.get_timekeeping(document_id)
        message = PrintUtils.pretty_print(training)
        reply_markup = CallbackUtils.get_reply_markup(UserState.EDIT, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message,
            reply_markup=reply_markup)

    async def handle_games(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.EDIT_TO_GAMES)

    async def handle_trainings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.EDIT_TO_TRAININGS)

    async def handle_timekeepings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.EDIT_TO_TIMEKEEPINGS)

    async def handle_overview(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # Distinguish UsersToState?
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.EDIT_OVERVIEW)
