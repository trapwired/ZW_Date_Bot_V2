from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState
from Enums.EventField import EventField
from Enums.AttendanceState import AttendanceState
from Enums.MessageType import MessageType

from domain.entities.UsersToState import UsersToState
from domain.entities.TempData import TempData, FIELD_ORDER

from data.DataAccess import DataAccess

from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService

from Utils import UpdateEventUtils
from Utils import PrintUtils
from Utils.CustomExceptions import NoTempDataFoundException

from features.adminpanel import AdminMenu
from features.events import EventsMenu

from domain import EventDateTimeParser


# The typed-input half of the add-event wizard (the buttons on the draft message are
# handled by AdminMenuCallbackNode). One node covers all event types: the draft
# (TempData) carries the type, and the current step lives in temp_data.step, walking
# FIELD_ORDER (games additionally collect an opponent); SAVE marks the finish step.


class AddEventFieldsNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_service = event_service
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.add_main_menu_escapes(self._discard_draft)
        self.fallback_action = self.handle_user_input

    def _discard_draft(self, user_to_state: UsersToState) -> None:
        try:
            temp_data = self.event_service.get_draft(user_to_state.user_id)
        except NoTempDataFoundException:
            return
        self.event_service.discard_draft(temp_data)

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._discard_draft(user_to_state)
        await self.telegram_service.send_message(
            update=update, all_buttons=None, message='Cancelled - the event was not saved.')

    async def handle_user_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        message = update.message.text.lower()
        try:
            temp_data = self.event_service.get_draft(user_to_state.user_id)
        except NoTempDataFoundException:
            # The draft is gone (e.g. discarded via a button) - recover to the main menu.
            self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
            await self.telegram_service.send_message(
                update=update, all_buttons=None,
                message='I lost track of that draft - please start again via the admin menu.')
            return

        # On the finish step, 'save' commits; anything else just re-prompts to save.
        if temp_data.step == EventField.SAVE:
            if message == 'save':
                await self.handle_save(update, user_to_state, temp_data)
                return
            await self._prompt_next(update, EventField.SAVE)
            return

        steps = FIELD_ORDER[temp_data.event_type]
        field = temp_data.step

        if field == EventField.DATETIME:
            parsed = EventDateTimeParser.parse_future(message)
            if not parsed.ok:
                # Parsing failed - report and stay on this step without mutating anything.
                await self.telegram_service.send_message(update=update, all_buttons=None, message=parsed.error)
                return
            temp_data.timestamp = parsed.value
        elif field == EventField.LOCATION:
            temp_data.location = message
        elif field == EventField.OPPONENT:
            temp_data.opponent = message

        index = steps.index(field)
        next_step = steps[index + 1] if index + 1 < len(steps) else EventField.SAVE
        temp_data.step = next_step
        self.event_service.save_draft(temp_data)

        await self.update_inline_message(temp_data, 'Adding new', can_save=(next_step == EventField.SAVE))
        await self._prompt_next(update, next_step)

    async def _prompt_next(self, update: Update, attribute: EventField) -> None:
        message = PrintUtils.get_update_attribute_message(attribute)
        await self.telegram_service.send_message(update=update, all_buttons=None, message=message)

    async def handle_save(self, update: Update, user_to_state: UsersToState, temp_data: TempData):
        new_event = self.event_service.finalize_draft(temp_data)
        await self.update_inline_message(temp_data, 'Saved', can_save=None)
        await self.notify_all_players(new_event, temp_data.event_type)
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self.telegram_service.send_message(update=update, all_buttons=None, message='Saved 👍')

    async def update_inline_message(self, temp_data: TempData, prefix: str, can_save: bool | None):
        """Re-render the draft message; can_save=None drops the buttons (draft finished)."""
        event_summary = PrintUtils.pretty_print(temp_data, temp_data.event_type)
        pretty_print = UpdateEventUtils.get_inline_message(prefix, temp_data.event_type, event_summary)
        reply_markup = None if can_save is None else AdminMenu.build_wizard_markup(can_save)
        await self.telegram_service.edit_inline_message_text(pretty_print, temp_data.query_id, temp_data.chat_id,
                                                             reply_markup)

    async def notify_all_players(self, new_event, event_type):
        all_players = self.event_service.get_all_players()

        for player in all_players:
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message_type=MessageType.EVENT_ADDED)

            pretty_print_event = PrintUtils.pretty_print(new_event, AttendanceState.UNSURE)
            reply_markup = EventsMenu.build_attendance_markup(event_type, new_event.doc_id)
            message_text = PrintUtils.event_label(event_type) + ' | ' + pretty_print_event
            await self.telegram_service.send_message(
                update=player,
                all_buttons=None,
                message=message_text,
                reply_markup=reply_markup)
