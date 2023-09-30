from Enums.UserState import UserState
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DELIMITER = '-'
ATTENDANCE_STATE_OPTIONS = [CallbackOption.YES, CallbackOption.NO, CallbackOption.UNSURE]
YES_OR_NO_OPTIONS = [CallbackOption.YES, CallbackOption.NO]
UPDATE_OR_DELETE_OPTIONS = [CallbackOption.UPDATE, CallbackOption.DELETE]
UPDATE_GAME_OPTIONS = [CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.OPPONENT]
UPDATE_TRAINING_OPTIONS = [CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.OPPONENT]
UPDATE_TKE_OPTIONS = [CallbackOption.DATETIME, CallbackOption.LOCATION]


def get_edit_event_reply_markup(user_state: UserState, event_type: Event, document_id: str):
    return _get_reply_markup(ATTENDANCE_STATE_OPTIONS, user_state, event_type, document_id)


def get_update_or_delete_reply_markup(event_type: Event, document_id: str):
    return _get_reply_markup(UPDATE_OR_DELETE_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)


def get_yes_or_no_markup(event_type: Event, document_id: str):
    return _get_reply_markup(YES_OR_NO_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)


def _get_reply_markup(options: [CallbackOption], user_state: UserState, event_type: Event, document_id: str):
    button_list = []
    for option in options:
        new_button = InlineKeyboardButton(option.name,
                                          callback_data=get_callback_message(user_state, event_type, option,
                                                                             document_id))
        button_list.append(new_button)
    return InlineKeyboardMarkup([button_list])


def get_callback_message(user_state: UserState, event_type: Event, option: CallbackOption, doc_id: str):
    return user_state.name + DELIMITER + event_type.name + DELIMITER + option.name + DELIMITER + doc_id


def try_parse_callback_message(message: str) -> tuple[UserState, Event, CallbackOption, str] | None:
    split = message.split(DELIMITER)
    if len(split) != 4:
        return None

    try:
        user_state = UserState[split[0]]
        event = Event[split[1]]
        callback_option = CallbackOption[split[2]]
        doc_id = split[3]
    except KeyError:
        return None

    return user_state, event, callback_option, doc_id
