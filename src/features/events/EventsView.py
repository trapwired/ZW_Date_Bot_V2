"""Renders the two screens of the events menu - the event list and the event card -
as (text, inline markup) pairs. Pure presentation on top of the services; the
callback node decides when to send vs. edit."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role
from Enums.RoleSet import RoleSet

from Utils import Format
from Utils import PrintUtils

from features.events import EventsMenu

EVENT_TYPES_IN_ORDER = [Event.GAME, Event.TRAINING, Event.TIMEKEEPING]


class EventsView:
    def __init__(self, event_service, attendance_service, statistics_service):
        self.event_service = event_service
        self.attendance_service = attendance_service
        self.statistics_service = statistics_service

    PAGE_SIZE = 8

    def build_list(self, role: Role, telegram_id: int, selected_type: Event | None,
                   page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
        available_types = self._available_types(role)
        if len(available_types) == 0:
            return 'There are no upcoming events at the moment.', None
        if selected_type not in available_types:
            selected_type = available_types[0]

        events = self.event_service.get_upcoming(selected_type)
        last_page = max(0, (len(events) - 1) // self.PAGE_SIZE)
        page = min(max(page, 0), last_page)
        page_of_events = events[page * self.PAGE_SIZE:(page + 1) * self.PAGE_SIZE]

        own_attendances = {}
        if role is not Role.SPECTATOR:
            own_attendances = self.attendance_service.get_own_attendances(telegram_id)

        rows = []
        if len(available_types) > 1:
            rows.append(EventsMenu.build_filter_row(available_types))
        for event in page_of_events:
            rows.append([InlineKeyboardButton(
                self._list_button_label(event, own_attendances, role),
                callback_data=EventsMenu.encode_card(selected_type, event.doc_id))])
        if last_page > 0:
            rows.append(EventsMenu.build_page_row(selected_type, page, last_page))

        text = (f'{Format.bold(f"Upcoming {EventsMenu.FILTER_LABELS[selected_type]}")}\n'
                'Tap an event for details' + ('' if role is Role.SPECTATOR else ' or to change your attendance') + ':')
        return text, InlineKeyboardMarkup(rows)

    def build_card(self, role: Role, telegram_id: int, event_type: Event, doc_id: str) -> tuple[str, InlineKeyboardMarkup]:
        event = self.event_service.get_event(event_type, doc_id)
        event_summary = PrintUtils.pretty_print_long(event) if event_type is Event.GAME else PrintUtils.pretty_print(event)
        stats_with_names = self.statistics_service.get_event_attendance_summary(doc_id, event_type)

        header = PrintUtils.event_label(event_type) + ': ' + event_summary
        text = PrintUtils.pretty_print_event_summary(stats_with_names, header, event_type)

        can_attend = role in RoleSet.PLAYERS
        if can_attend:
            own = self.attendance_service.get_attendance(telegram_id, doc_id, event_type)
            if self._timekeeping_is_full_for(event, event_type, own):
                can_attend = False
                text += '\n' + Format.italic('Already enough people registered for this event.')
            else:
                text += '\nYour answer: ' + PrintUtils.pretty_print_attendance(own.state)

        markup = EventsMenu.build_card_markup(event_type, doc_id, can_attend, is_admin=(role is Role.ADMIN))
        return text, markup

    def _available_types(self, role: Role) -> list[Event]:
        # Timekeeping events are deliberately hidden from spectators.
        types = [t for t in EVENT_TYPES_IN_ORDER if self.event_service.any_upcoming(t)]
        if role is Role.SPECTATOR:
            types = [t for t in types if t is not Event.TIMEKEEPING]
        return types

    def _list_button_label(self, event, own_attendances: dict, role: Role) -> str:
        label = PrintUtils.pretty_print_event_command(event)
        if role is Role.SPECTATOR:
            return label
        # Players without a stored answer count as unsure (same rule as the summaries).
        attendance = own_attendances.get(event.doc_id)
        state = attendance.state if attendance else AttendanceState.UNSURE
        return f'{PrintUtils.ATTENDANCE_EMOJI[state]} {label}'

    def _timekeeping_is_full_for(self, event, event_type: Event, own_attendance) -> bool:
        # A full timekeeping event only locks out players who are not part of the
        # yes-crowd; whoever already said yes may still change their answer.
        if event_type is not Event.TIMEKEEPING or own_attendance.state is AttendanceState.YES:
            return False
        return self.attendance_service.yes_count(event.doc_id, event_type) >= event.people_required
