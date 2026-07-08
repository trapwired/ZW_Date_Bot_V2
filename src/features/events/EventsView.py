"""Renders the two screens of the events menu - the event list and the event card -
as (text, inline markup) pairs. Pure presentation on top of the services; the
callback node decides when to send vs. edit."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role
from Enums import Audience

from Utils import Format
from Utils import PrintUtils

from features.events import EventsMenu
from features.language import LanguageMenu

from localization.Translator import t

EVENT_TYPES_IN_ORDER = [Event.GAME, Event.TRAINING, Event.TIMEKEEPING]


class EventsView:
    PAGE_SIZE = 8

    def __init__(self, event_service, attendance_service, statistics_service):
        self.event_service = event_service
        self.attendance_service = attendance_service
        self.statistics_service = statistics_service

    def build_list(self, user_to_state, telegram_id: int, selected_type: Event | None,
                   page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
        role = user_to_state.role
        events_by_type = self._upcoming_by_type(role)
        if len(events_by_type) == 0:
            # Even the empty list keeps the language entry - a new member's first
            # screen is often this one.
            return (t('There are no upcoming events at the moment.'),
                    InlineKeyboardMarkup([LanguageMenu.build_entry_row()]))
        available_types = list(events_by_type.keys())
        if selected_type not in events_by_type:
            selected_type = available_types[0]

        events = events_by_type[selected_type]
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
        # The per-member language switch lives on the menu every member opens.
        rows.append(LanguageMenu.build_entry_row())

        header = t('<b>Upcoming {event_type}</b>',
                   event_type=Format.escape(t(EventsMenu.FILTER_LABELS[selected_type])))
        instruction = (t('Tap an event for details:') if role is Role.SPECTATOR
                       else t('Tap an event for details or to change your attendance:'))
        text = header + '\n' + instruction
        return text, InlineKeyboardMarkup(rows)

    def build_card(self, user_to_state, telegram_id: int, event_type: Event, doc_id: str) -> tuple[str, InlineKeyboardMarkup]:
        role = user_to_state.role
        event = self.event_service.get_event(event_type, doc_id)
        event_summary = PrintUtils.pretty_print_long(event) if event_type is Event.GAME else PrintUtils.pretty_print(event)
        stats_with_names = self.statistics_service.get_event_attendance_summary(doc_id, event_type)

        header = PrintUtils.event_label(event_type) + ': ' + event_summary
        text = PrintUtils.pretty_print_event_summary(stats_with_names, header, event_type)

        can_attend = Audience.PLAYERS.allows(user_to_state)
        if can_attend:
            own = self.attendance_service.get_attendance(telegram_id, doc_id, event_type)
            if event_type is Event.TIMEKEEPING and \
                    self.attendance_service.timekeeping_is_locked(own, event, yes_count=len(stats_with_names[0])):
                can_attend = False
                text += '\n' + t('<i>Already enough people registered for this event.</i>')
            else:
                text += '\n' + t('Your answer: {answer}', answer=PrintUtils.pretty_print_attendance(own.state))

        markup = EventsMenu.build_card_markup(event_type, doc_id, can_attend, is_admin=user_to_state.is_admin)
        return text, markup

    def _upcoming_by_type(self, role: Role) -> dict[Event, list]:
        # Timekeeping events are deliberately hidden from spectators.
        types = [t for t in EVENT_TYPES_IN_ORDER
                 if not (role is Role.SPECTATOR and t is Event.TIMEKEEPING)]
        by_type = {t: self.event_service.get_upcoming(t) for t in types}
        return {t: events for t, events in by_type.items() if len(events) > 0}

    def _list_button_label(self, event, own_attendances: dict, role: Role) -> str:
        label = PrintUtils.pretty_print_event_command(event)
        if role is Role.SPECTATOR:
            return label
        # Players without a stored answer count as unsure (same rule as the summaries).
        attendance = own_attendances.get(event.doc_id)
        state = attendance.state if attendance else AttendanceState.UNSURE
        return f'{PrintUtils.ATTENDANCE_EMOJI[state]} {label}'
