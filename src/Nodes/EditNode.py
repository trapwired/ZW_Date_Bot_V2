from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils

from src.Utils import CallbackUtils


class EditNode(Node):

    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                              document_id: str):
        game = self.data_access.get_game(document_id)
        message = PrintUtils.pretty_print(game)
        # TODO add message? Add summary into string? (update needed...)

        options = ['Yes', 'No', 'Unsure']
        button_list = []
        for option in options:
            new_button = \
                InlineKeyboardButton(option,
                                     callback_data=CallbackUtils.get_callback_message(UserState.EDIT, option,
                                                                                      document_id))
            button_list.append(new_button)
        reply_markup = InlineKeyboardMarkup([button_list])

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
