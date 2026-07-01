from telegram import Update

from Nodes.Node import Node

from domain import EventDateTimeParser
from domain import AttendanceResetPolicy

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


class EditEventFieldNode(Node):
    """Applies a single-field edit to an existing event. Which event, which field, and
    which inline message to update all come from the caller's context
    (user_to_state.additional_info, set by UpdateEventCallbackNode) rather than from the
    UserState, so one node handles every event-type/field combination."""

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, node_handler, event_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.ADMIN)
        self.node_handler = node_handler
        self.event_service = event_service

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_event_field(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        edit = CallbackUtils.try_parse_additional_information(user_to_state.additional_info)
        if not edit:
            return await self.handle_parse_additional_info_failed(user_to_state, update)

        message = update.message.text.lower()

        old_event = None
        if edit.field == CallbackOption.DATETIME:
            parsed = EventDateTimeParser.parse_future(message)
            if not parsed.ok:
                # Parsing failed - report and stay on this step without changing anything.
                await self.telegram_service.send_message_with_normal_keyboard(update=update, message=parsed.error)
                return
            old_event = self.event_service.get_event(edit.event_type, edit.doc_id)
            new_value = parsed.value
        else:
            new_value = message

        updated_event = self.event_service.update_field(edit.event_type, edit.doc_id, new_value, edit.field)

        new_inline_message = UpdateEventUtils.get_inline_message('Updated', edit.event_type, updated_event)
        await self.telegram_service.edit_inline_message_text(new_inline_message, edit.message_id, edit.chat_id)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message="Updated event successfully!")
        self.node_handler.recalculate_node_transitions()

        if old_event is not None and AttendanceResetPolicy.requires_attendance_reset(old_event.timestamp,
                                                                                     updated_event.timestamp):
            await self.notify_all_players(edit.event_type, edit.doc_id, updated_event, old_event)
            text = ('Since the event was moved by more than 2 hours, I invalidated all previous answers and let all '
                    'players know...')
            await self.telegram_service.send_message_with_normal_keyboard(update=update, message=text)

        # handle_cancel does the authoritative reset: state -> ADMIN, clear additional_info, render the admin menu.
        await self.handle_cancel(update, user_to_state, UserState.ADMIN)

    async def notify_all_players(self, event_type: Event, doc_id: str, updated_event, old_event):
        self.event_service.reset_attendance(event_type, doc_id)
        all_players = self.event_service.get_all_players()
        pretty_print_old_event = PrintUtils.pretty_print_event_datetime(old_event)

        for player in all_players:
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message_type=MessageType.EVENT_TIMESTAMP_CHANGED,
                message_extra_text=pretty_print_old_event)

            pretty_print_event = PrintUtils.pretty_print(updated_event, AttendanceState.UNSURE)
            reply_markup = CallbackUtils.get_edit_event_reply_markup(UserState.EDIT, event_type, doc_id)
            message_text = PrintUtils.event_label(event_type) + ' | ' + pretty_print_event
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)

    async def handle_parse_additional_info_failed(self, user_to_state: UsersToState, update: Update):
        text = 'Error getting information from the database, please restart updating an event via the menu :)'
        new_state = UserState.ADMIN_UPDATE
        self.user_state_service.update_user_state(user_to_state, new_state)

        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=text)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN_UPDATE)

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        await self.handle_event_field(update, user_to_state, new_state)
