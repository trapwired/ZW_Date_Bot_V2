from Enums.UserState import UserState
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DELIMITER = '-'
OPTIONS = [AttendanceState.YES, AttendanceState.NO, AttendanceState.UNSURE]


def get_reply_markup(user_state: UserState, event_type: Event, document_id: str):
    button_list = []
    for option in OPTIONS:
        new_button = InlineKeyboardButton(option.name,
                                          callback_data=get_callback_message(user_state, event_type, option, document_id))
        button_list.append(new_button)
    return InlineKeyboardMarkup([button_list])


def get_callback_message(user_state: UserState, event_type: Event, option: AttendanceState, doc_id: str):
    return user_state.name + DELIMITER + event_type.name + DELIMITER + option.name + DELIMITER + doc_id


def try_parse_callback_message(message: str) -> tuple[UserState, Event, AttendanceState, str] | None:
    split = message.split(DELIMITER)
    if len(split) != 4:
        return None

    try:
        user_state = UserState[split[0]]
        event = Event[split[1]]
        attendance_state = AttendanceState[split[2]]
        doc_id = split[3]
    except KeyError:
        return None

    return user_state, event, attendance_state, doc_id
