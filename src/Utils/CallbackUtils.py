from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DELIMITER = '#'
ATTENDANCE_STATE_OPTIONS = [CallbackOption.YES, CallbackOption.NO, CallbackOption.UNSURE]
YES_OR_NO_OPTIONS = [CallbackOption.YES, CallbackOption.NO]
UPDATE_OR_DELETE_OPTIONS = [CallbackOption.UPDATE, CallbackOption.DELETE]
UPDATE_GAME_OPTIONS = [CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.OPPONENT, CallbackOption.Back]
UPDATE_TRAINING_OPTIONS = [CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.Back]
UPDATE_TKE_OPTIONS = [CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.Back]


def get_update_event_options(event_type: Event, document_id: str):
    match event_type:
        case Event.GAME:
            return _get_reply_markup(UPDATE_GAME_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)
        case Event.TRAINING:
            return _get_reply_markup(UPDATE_TRAINING_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)
        case Event.TIMEKEEPING:
            return _get_reply_markup(UPDATE_TKE_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)


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


def build_additional_information(message_id: int, chat_id: int, event_document_id: str) -> str:
    return str(message_id) + DELIMITER + str(chat_id) + DELIMITER + event_document_id


def try_parse_additional_information(message: str) -> tuple[int, int, str] | None:
    split = message.split(DELIMITER)
    if len(split) != 3:
        return None

    try:
        message_id = int(split[0])
        chat_id = int(split[1])
        doc_id = split[2]
    except KeyError:
        return None

    return message_id, chat_id, doc_id
