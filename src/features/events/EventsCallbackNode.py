import os

from telegram import Update, InputFile

from framework.Nodes.CallbackNode import CallbackNode

from Enums.AttendanceState import AttendanceState
from Enums.EventField import EventField
from Enums.Event import Event
from Enums.Role import Role
from Enums.RoleSet import RoleSet
from Enums.UserState import UserState

from data.DataAccess import DataAccess

from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService
from framework.Services.UserStateService import UserStateService
from framework.Triggers.TriggerPayload import TriggerPayload

from features.attendance.IcsService import IcsService
from features.events import EventsMenu
from features.events.EventsView import EventsView

from domain.entities.TempData import FIELD_ORDER

from Utils import CallbackUtils
from Utils import PrintUtils
from Utils.CustomExceptions import ObjectNotFoundException


class EventsCallbackNode(CallbackNode):
    """Handles every press inside the events menu. The whole flow lives on one inline
    message (list <-> card <-> admin actions), so no UserState is involved except when
    an admin starts typing a new field value."""

    required_roles = RoleSet.EVERYONE

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, ics_service: IcsService, attendance_service,
                 event_service, events_view: EventsView):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.ics_service = ics_service
        self.attendance_service = attendance_service
        self.event_service = event_service
        self.events_view = events_view

    async def handle(self, update: Update):
        query = update.callback_query
        if EventsMenu.is_legacy_attendance_callback(query.data):
            parsed = EventsMenu.try_parse_legacy_attendance(query.data)
        else:
            parsed = EventsMenu.parse(query.data)
        if parsed is None:
            await query.answer()
            return
        action, event_type, args = parsed

        role = self.user_state_service.get_user_state(update.effective_chat.id).role
        telegram_id = update.effective_chat.id

        if event_type is Event.TIMEKEEPING and role not in RoleSet.PLAYERS:
            # Timekeeping events are hidden from spectators; a forwarded button must
            # not leak the card, attendance names or the calendar file either.
            await query.answer()
            return

        match action:
            case EventsMenu.LIST:
                page = int(args[0]) if args else 0
                await self._show_list(query, role, telegram_id, event_type, page)
            case EventsMenu.CARD:
                await self._show_card(query, role, telegram_id, event_type, args[0])
            case EventsMenu.ATTEND if role in RoleSet.PLAYERS:
                await self._set_attendance(query, role, telegram_id, event_type, args[0],
                                           AttendanceState(int(args[1])))
            case EventsMenu.CALENDAR:
                await self._send_ics(query, update, event_type, args[0])
            case EventsMenu.EDIT_FIELDS if role is Role.ADMIN:
                await self._show_field_chooser(query, role, telegram_id, event_type, args[0])
            case EventsMenu.EDIT_FIELD if role is Role.ADMIN:
                await self._prompt_field_value(update, query, event_type, args[0], EventField(int(args[1])))
            case EventsMenu.DELETE if role is Role.ADMIN:
                await self._confirm_delete(query, role, telegram_id, event_type, args[0])
            case EventsMenu.DELETE_CONFIRMED if role is Role.ADMIN:
                await self._delete(query, event_type, args[0])
            case _:
                # Unknown action or a role that may not take it (e.g. a spectator
                # pressing a forwarded attendance button) - just dismiss the spinner.
                await query.answer()

    async def _show_list(self, query, role: Role, telegram_id: int, event_type: Event, page: int = 0):
        text, markup = self.events_view.build_list(role, telegram_id, event_type, page)
        await query.answer()
        await self.telegram_service.edit_callback_message(query, text, markup)

    async def _show_card(self, query, role: Role, telegram_id: int, event_type: Event, doc_id: str):
        await query.answer()
        await self._render_card(query, role, telegram_id, event_type, doc_id)

    async def _set_attendance(self, query, role: Role, telegram_id: int, event_type: Event, doc_id: str,
                              state: AttendanceState):
        try:
            if event_type is Event.TIMEKEEPING and state is AttendanceState.YES:
                # The card hides the buttons once the event is full, but stale cards and
                # pushed reminder messages keep live YES buttons - re-check on write.
                event = self.event_service.get_event(event_type, doc_id)
                own = self.attendance_service.get_attendance(telegram_id, doc_id, event_type)
                if self.attendance_service.timekeeping_is_locked(own, event):
                    await query.answer()
                    await self._render_card(query, role, telegram_id, event_type, doc_id)
                    return
            attendance, _ = self.attendance_service.set_attendance(telegram_id, event_type, doc_id, state)
        except ObjectNotFoundException:
            await self._show_event_gone(query, event_type)
            return
        await query.answer()
        await self._render_card(query, role, telegram_id, event_type, doc_id)

        trigger_payload = TriggerPayload(new_attendance=attendance, doc_id=doc_id, event_type=event_type)
        await self.trigger_service.check_triggers(trigger_payload)

    async def _send_ics(self, query, update: Update, event_type: Event, doc_id: str):
        try:
            ics_file_path = self.ics_service.get_ics(event_type, doc_id)
        except ObjectNotFoundException:
            await self._show_event_gone(query, event_type)
            return

        # Answer first so the button spinner clears even if the send fails.
        await query.answer()
        try:
            with open(ics_file_path, 'rb') as ics_file:
                await self.telegram_service.send_file(update, path=InputFile(ics_file))
        finally:
            os.remove(ics_file_path)

    async def _show_field_chooser(self, query, role: Role, telegram_id: int, event_type: Event, doc_id: str):
        try:
            text, _ = self.events_view.build_card(role, telegram_id, event_type, doc_id)
        except ObjectNotFoundException:
            await self._show_event_gone(query, event_type)
            return
        markup = EventsMenu.build_field_chooser_markup(event_type, doc_id, list(FIELD_ORDER[event_type]))
        await query.answer()
        await self.telegram_service.edit_callback_message(query, text + '\n\n' + 'Which field do you want to change?',
                                                          markup)

    async def _prompt_field_value(self, update: Update, query, event_type: Event, doc_id: str,
                                  field: EventField):
        if field not in FIELD_ORDER[event_type]:
            # The chooser never offers this combination (e.g. OPPONENT on a training), so
            # it is a forged or stale callback - fail loudly (maintainer alert) instead of
            # prompting for a value that would be written into a phantom field.
            raise ValueError(f'{event_type} has no {field.name} field to edit')

        # The admin types the new value next; remember which event/field/card message the
        # answer belongs to, and route their next text through the field-edit node.
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        user_to_state.additional_info = CallbackUtils.build_additional_information(
            query.message.id, query.message.chat_id, doc_id, event_type, field)
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_UPDATE_EVENT_FIELD)

        await query.answer()
        prompt = PrintUtils.get_update_attribute_message(field)
        await self.telegram_service.send_message(update=update, all_buttons=None, message=prompt)

    async def _confirm_delete(self, query, role: Role, telegram_id: int, event_type: Event, doc_id: str):
        try:
            text, _ = self.events_view.build_card(role, telegram_id, event_type, doc_id)
        except ObjectNotFoundException:
            await self._show_event_gone(query, event_type)
            return
        await query.answer()
        await self.telegram_service.edit_callback_message(
            query, text + '\n\n' + 'Really delete this event? This cannot be undone.',
            EventsMenu.build_delete_confirm_markup(event_type, doc_id))

    async def _delete(self, query, event_type: Event, doc_id: str):
        self.event_service.delete_event(event_type, doc_id)
        await query.answer()
        await self.telegram_service.edit_callback_message(
            query, f'Deleted {PrintUtils.event_label(event_type)} 👍',
            EventsMenu.build_back_to_list_markup(event_type))

    async def _render_card(self, query, role: Role, telegram_id: int, event_type: Event, doc_id: str):
        try:
            text, markup = self.events_view.build_card(role, telegram_id, event_type, doc_id)
        except ObjectNotFoundException:
            await self._show_event_gone(query, event_type)
            return
        await self.telegram_service.edit_callback_message(query, text, markup)

    async def _show_event_gone(self, query, event_type: Event):
        await query.answer()
        await self.telegram_service.edit_callback_message(
            query, 'This event no longer exists.', EventsMenu.build_back_to_list_markup(event_type))
