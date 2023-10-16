from Nodes.Node import Node
from telegram import Update

from Enums.UserState import UserState
from Enums.MessageType import MessageType
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.UsersToState import UsersToState

from Utils import UpdateEventUtils
from Utils import CallbackUtils

from Data.DataAccess import DataAccess
from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService


class EditEventLocationOrOpponentNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_type: Event, string_type: CallbackOption):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.string_type = string_type
        self.event_type = event_type
        self.add_cancel_transition()

    def add_cancel_transition(self):
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.ADMIN)

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_event_timestamp(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # TODO call this function? how is it called? --> rename, adjust logic, cursor is HERE!!
        message = update.message.text.lower()

        parsed_string = UpdateEventUtils.parse_datetime_string(message)
        if type(parsed_string) is str:
            # Error case, send message without changing anything
            await self.telegram_service.send_message_with_normal_keyboard(
                update=update,
                message=parsed_string)
            return

        new_datetime = parsed_string

        try_parse = CallbackUtils.try_parse_additional_information(user_to_state.additional_info)
        if not try_parse:
            return await self.handle_parse_additional_info_failed(user_to_state, update)

        doc_id, message_id = try_parse

        # store in db - store response element for pretty print
        updated_event = self.data_access.update_event_field(self.event_type, doc_id, new_datetime, CallbackOption.DATETIME)

        # Update inline_message with new string
        new_inline_message = UpdateEventUtils.get_inline_message('Updated', self.event_type, updated_event)
        await self.telegram_service.edit_inline_message_text(new_inline_message, message_id)

        # new user state?
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)
        # send response: update ok
        text = "Updated event successfully!"
        await self.telegram_service.send_message_with_normal_keyboard(
            update=update,
            message=text)

        await self.handle_cancel(update, user_to_state, UserState.ADMIN)

    async def handle_parse_additional_info_failed(self, user_to_state: UsersToState, update: Update):
        text = 'Error getting information from the database, please restart updating a event via the menu :)'
        new_state = UserState.ADMIN_UPDATE
        self.user_state_service.update_user_state(user_to_state, new_state)

        await self.telegram_service.send_message_with_normal_keyboard(
            update=update,
            message=text)

        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_UPDATE)
        return
