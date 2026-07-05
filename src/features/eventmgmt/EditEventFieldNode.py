from telegram import Update

from framework.Nodes.Node import Node

from domain import EventDateTimeParser
from domain import AttendanceResetPolicy

from Enums.UserState import UserState
from Enums.MessageType import MessageType
from Enums.Event import Event
from Enums.EventField import EventField

from domain.entities.UsersToState import UsersToState

from Utils import CallbackUtils
from Utils import PrintUtils

from data.DataAccess import DataAccess
from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService

from features.eventmgmt import PlayerNotifications
from features.events.EventsView import EventsView

from localization.Translator import t


class EditEventFieldNode(Node):
    """Applies a single-field edit to an existing event. Which event, which field, and
    which event-card message to refresh all come from the caller's context
    (user_to_state.additional_info, set by EventsCallbackNode) rather than from the
    UserState, so one node handles every event-type/field combination."""

    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_service, events_view: EventsView):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_service = event_service
        self.events_view = events_view
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.enable_main_menu_escapes(self._clear_edit_context)
        self.fallback_action = self.handle_event_field

    def _clear_edit_context(self, user_to_state: UsersToState) -> None:
        user_to_state.additional_info = ''

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._clear_edit_context(user_to_state)
        await self.telegram_service.send_message(
            update=update, all_buttons=None, message=t('Cancelled - the event was not changed.'))

    async def handle_event_field(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        edit = CallbackUtils.try_parse_additional_information(user_to_state.additional_info)
        if not edit:
            return await self.handle_parse_additional_info_failed(user_to_state, update)

        message = update.message.text.lower()

        old_event = None
        if edit.field == EventField.DATETIME:
            parsed = EventDateTimeParser.parse_future(message)
            if not parsed.ok:
                # Parsing failed - report and stay on this step without changing anything.
                await self.telegram_service.send_message(update=update, all_buttons=None, message=parsed.error)
                return
            old_event = self.event_service.get_event(edit.event_type, edit.doc_id)
            new_value = parsed.value
        else:
            new_value = message

        updated_event = self.event_service.update_field(edit.event_type, edit.doc_id, new_value, edit.field)

        await self._refresh_event_card(user_to_state, edit)
        # The prompt is consumed - drop it so the chat doesn't fill up.
        await self.telegram_service.delete_message(edit.prompt_message_id, edit.chat_id)
        await self.telegram_service.send_message(update=update, all_buttons=None,
                                                 message=t('Updated event successfully!'))

        if old_event is not None and AttendanceResetPolicy.requires_attendance_reset(old_event.timestamp,
                                                                                     updated_event.timestamp):
            await self.notify_all_players(edit.event_type, edit.doc_id, updated_event, old_event)
            text = t('Since the event was moved by more than 2 hours, I invalidated all previous answers and let all '
                     'players know...')
            await self.telegram_service.send_message(update=update, all_buttons=None, message=text)

        self._clear_edit_context(user_to_state)
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)

    async def _refresh_event_card(self, user_to_state: UsersToState, edit: CallbackUtils.EventFieldEdit):
        text, markup = self.events_view.build_card(user_to_state.role, edit.chat_id, edit.event_type, edit.doc_id)
        await self.telegram_service.edit_inline_message_text(text, edit.message_id, edit.chat_id, markup)

    async def notify_all_players(self, event_type: Event, doc_id: str, updated_event, old_event):
        self.event_service.reset_attendance(event_type, doc_id)
        await PlayerNotifications.push_event_to_players(
            self.telegram_service, self.data_access, self.event_service.get_all_players(), updated_event, event_type,
            intro_message_type=MessageType.EVENT_TIMESTAMP_CHANGED,
            intro_extra_text=PrintUtils.pretty_print_event_datetime(old_event))

    async def handle_parse_additional_info_failed(self, user_to_state: UsersToState, update: Update):
        text = t('Error getting information from the database, please restart updating the event via the events menu :)')
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self.telegram_service.send_message(update=update, all_buttons=None, message=text)
