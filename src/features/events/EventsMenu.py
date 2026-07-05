"""Inline menu for browsing upcoming events: event list -> event card -> actions.

Dedicated callback channel for the events slice, kept separate from the roles
(ROLES#...) and admin-menu (AP#...) channels so each domain owns its encoding.
NodeHandler routes on PREFIX.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from localization.Translator import t

PREFIX = 'EV'
DELIMITER = '#'

# Actions (kept short to stay well under Telegram's 64-byte callback_data limit).
LIST = 'L'              # show the event list for one event type
CARD = 'C'              # show one event's card
ATTEND = 'A'            # set own attendance, re-render the card
CALENDAR = 'I'          # send the event as an .ics file
EDIT_FIELDS = 'E'       # admin: swap the card's buttons for the field chooser
EDIT_FIELD = 'F'        # admin: prompt for a new value of one field
DELETE = 'D'            # admin: ask for delete confirmation
DELETE_CONFIRMED = 'X'  # admin: delete the event

FILTER_LABELS = {Event.GAME: 'Games', Event.TRAINING: 'Trainings', Event.TIMEKEEPING: 'Timekeeping'}

# The pre-redesign attendance buttons encoded 'EDIT#<Event>#<option>#<doc_id>'. Those
# buttons live on reminder/notification messages already sitting in player chats, so
# they must keep working; see try_parse_legacy_attendance.
LEGACY_PREFIX = 'EDIT' + DELIMITER
_LEGACY_ATTENDANCE_OPTIONS = {state.name: state for state in AttendanceState}
_LEGACY_CALENDAR_OPTION = 'CALENDAR'


def encode_list(event_type: Event, page: int = 0) -> str:
    if page == 0:
        # Page 0 stays the bare form so existing buttons (cards' back-to-list,
        # filter row) keep one canonical encoding.
        return _join(LIST, int(event_type))
    return _join(LIST, int(event_type), page)


def encode_card(event_type: Event, doc_id: str) -> str:
    return _join(CARD, int(event_type), doc_id)


def encode_attend(event_type: Event, doc_id: str, state: AttendanceState) -> str:
    return _join(ATTEND, int(event_type), doc_id, int(state))


def encode_calendar(event_type: Event, doc_id: str) -> str:
    return _join(CALENDAR, int(event_type), doc_id)


def encode_edit_fields(event_type: Event, doc_id: str) -> str:
    return _join(EDIT_FIELDS, int(event_type), doc_id)


def encode_edit_field(event_type: Event, doc_id: str, field) -> str:
    return _join(EDIT_FIELD, int(event_type), doc_id, int(field))


def encode_delete(event_type: Event, doc_id: str) -> str:
    return _join(DELETE, int(event_type), doc_id)


def encode_delete_confirmed(event_type: Event, doc_id: str) -> str:
    return _join(DELETE_CONFIRMED, int(event_type), doc_id)


def _join(*parts) -> str:
    return DELIMITER.join([PREFIX, *[str(p) for p in parts]])


def is_events_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> tuple[str, Event, list[str]] | None:
    """-> (action, event_type, remaining args) or None if the data is not ours/malformed."""
    if not is_events_callback(data):
        return None
    parts = data.split(DELIMITER)
    if len(parts) < 3:
        return None
    try:
        return parts[1], Event(int(parts[2])), parts[3:]
    except ValueError:
        return None


def is_legacy_attendance_callback(data: str) -> bool:
    return data.startswith(LEGACY_PREFIX)


def try_parse_legacy_attendance(data: str) -> tuple[str, Event, list[str]] | None:
    """Translate an old-format attendance/calendar button press into the (action,
    event_type, args) shape parse() returns, so old messages keep working."""
    parts = data.split(DELIMITER)
    if len(parts) != 4:
        return None
    _, event_name, option_name, doc_id = parts
    try:
        event_type = Event[event_name]
    except KeyError:
        return None
    if option_name in _LEGACY_ATTENDANCE_OPTIONS:
        return ATTEND, event_type, [doc_id, str(int(_LEGACY_ATTENDANCE_OPTIONS[option_name]))]
    if option_name == _LEGACY_CALENDAR_OPTION:
        return CALENDAR, event_type, [doc_id]
    return None


###########
# MARKUPS #
###########

def build_filter_row(available_types: list[Event]) -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(t(FILTER_LABELS[event_type]), callback_data=encode_list(event_type))
            for event_type in available_types]


def build_page_row(event_type: Event, page: int, last_page: int) -> list[InlineKeyboardButton]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(t('« previous'), callback_data=encode_list(event_type, page - 1)))
    row.append(InlineKeyboardButton(t('{current}/{total}', current=page + 1, total=last_page + 1),
                                    callback_data=encode_list(event_type, page)))
    if page < last_page:
        row.append(InlineKeyboardButton(t('more »'), callback_data=encode_list(event_type, page + 1)))
    return row


def build_attendance_row(event_type: Event, doc_id: str) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(t('✅ Yes'), callback_data=encode_attend(event_type, doc_id, AttendanceState.YES)),
        InlineKeyboardButton(t('❌ No'), callback_data=encode_attend(event_type, doc_id, AttendanceState.NO)),
        InlineKeyboardButton(t('❓ Unsure'), callback_data=encode_attend(event_type, doc_id, AttendanceState.UNSURE)),
    ]


def build_attendance_markup(event_type: Event, doc_id: str) -> InlineKeyboardMarkup:
    """Buttons for event messages pushed to players (new event, reminder, moved event)."""
    return InlineKeyboardMarkup([
        build_attendance_row(event_type, doc_id),
        [InlineKeyboardButton(t('📅 Export to calendar'), callback_data=encode_calendar(event_type, doc_id))],
    ])


def build_card_markup(event_type: Event, doc_id: str, can_attend: bool, is_admin: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_attend:
        rows.append(build_attendance_row(event_type, doc_id))
    rows.append([InlineKeyboardButton(t('📅 Export to calendar'), callback_data=encode_calendar(event_type, doc_id))])
    if is_admin:
        rows.append([InlineKeyboardButton(t('✏️ Edit event'), callback_data=encode_edit_fields(event_type, doc_id)),
                     InlineKeyboardButton(t('🗑 Delete event'), callback_data=encode_delete(event_type, doc_id))])
    rows.append([InlineKeyboardButton(t('« Back to list'), callback_data=encode_list(event_type))])
    return InlineKeyboardMarkup(rows)


def build_field_chooser_markup(event_type: Event, doc_id: str, editable_fields: list) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(field.name.title(), callback_data=encode_edit_field(event_type, doc_id, field))
             for field in editable_fields]]
    rows.append([InlineKeyboardButton(t('« Back'), callback_data=encode_card(event_type, doc_id))])
    return InlineKeyboardMarkup(rows)


def build_delete_confirm_markup(event_type: Event, doc_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('Yes, delete it'), callback_data=encode_delete_confirmed(event_type, doc_id))],
        [InlineKeyboardButton('« Back', callback_data=encode_card(event_type, doc_id))],
    ])


def build_back_to_list_markup(event_type: Event) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('« Back to list'), callback_data=encode_list(event_type))]])
