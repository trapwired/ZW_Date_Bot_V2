from Nodes.Node import Node
from telegram import Update
import pandas as pd

from Enums.UserState import UserState
from Enums.MessageType import MessageType
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.AttendanceState import AttendanceState

from databaseEntities.UsersToState import UsersToState

from Utils import UpdateEventUtils
from Utils import CallbackUtils
from Utils import PrintUtils

from Data.DataAccess import DataAccess
from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService


class EditEventTimestampNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_type: Event, node_handler):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_type = event_type
        self.add_cancel_transition()
        self.node_handler = node_handler

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
        message = update.message.text.lower()

        parsed_datetime = UpdateEventUtils.parse_datetime_string(message)
        if type(parsed_datetime) is str:
            # Error case, send message without changing anything
            await self.telegram_service.send_message_with_normal_keyboard(
                update=update,
                message=parsed_datetime)
            return

        new_datetime = parsed_datetime

        try_parse = CallbackUtils.try_parse_additional_information(user_to_state.additional_info)
        if not try_parse:
            return await self.handle_parse_additional_info_failed(user_to_state, update)

        message_id, chat_id, doc_id = try_parse

        old_event = self.data_access.get_event(self.event_type, doc_id)

        updated_event = self.data_access.update_event_field(self.event_type, doc_id, new_datetime,
                                                            CallbackOption.DATETIME)

        # Update inline_message with new string
        new_inline_message = UpdateEventUtils.get_inline_message('Updated', self.event_type, updated_event)
        await self.telegram_service.edit_inline_message_text(new_inline_message, message_id, chat_id)

        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)

        text = "Updated event successfully!"
        await self.telegram_service.send_message_with_normal_keyboard(
            update=update,
            message=text)

        self.node_handler.recalculate_node_transitions()

        if abs(old_event.timestamp - updated_event.timestamp) > pd.Timedelta(hours=2):
            await self.notify_all_players(doc_id, updated_event, old_event)
            text = 'Since the event was moved by more than 2 hours, I invalidated all previous answers and let all players know...'
            await self.telegram_service.send_message_with_normal_keyboard(
                update=update,
                message=text)

        await self.handle_cancel(update, user_to_state, UserState.ADMIN)

    async def notify_all_players(self, doc_id: str, updated_event: Event, old_event: Event):
        self.data_access.reset_all_player_event_attendance(self.event_type, doc_id)
        # notify all players, give option to vote again

        all_players = self.data_access.get_all_players()

        pretty_print_old_event = PrintUtils.pretty_print_event_datetime(old_event)

        for player in all_players:
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message_type=MessageType.EVENT_TIMESTAMP_CHANGED,
                message_extra_text=pretty_print_old_event)

            pretty_print_event = PrintUtils.pretty_print(updated_event, AttendanceState.UNSURE)
            reply_markup = CallbackUtils.get_edit_event_reply_markup(
                UserState.EDIT,
                self.event_type,
                doc_id)
            message_text = self.event_type.name.lower().title() + ' | ' + pretty_print_event
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)

    async def handle_parse_additional_info_failed(self, user_to_state: UsersToState, update: Update):
        text = 'Error getting information from the database, please restart updating an event via the menu :)'
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

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        await self.handle_event_timestamp(update, user_to_state, new_state)
