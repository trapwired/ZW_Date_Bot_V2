from typing import NamedTuple

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
ADD_EVENT_OPTIONS = [CallbackOption.RESTART, CallbackOption.CANCEL]
FINISH_ADD_EVENT_OPTIONS = [CallbackOption.SAVE, CallbackOption.RESTART, CallbackOption.CANCEL]


def get_update_event_options(event_type: Event, document_id: str):
    match event_type:
        case Event.GAME:
            return _get_reply_markup(UPDATE_GAME_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)
        case Event.TRAINING:
            return _get_reply_markup(UPDATE_TRAINING_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)
        case Event.TIMEKEEPING:
            return _get_reply_markup(UPDATE_TKE_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)


def get_add_event_reply_markup(user_state: UserState, event_type: Event, document_id: str):
    return _get_reply_markup(ADD_EVENT_OPTIONS, user_state, event_type, document_id)


def get_finish_add_event_reply_markup(user_state: UserState, event_type: Event, document_id: str):
    return _get_reply_markup(FINISH_ADD_EVENT_OPTIONS, user_state, event_type, document_id)


def get_edit_event_reply_markup(user_state: UserState, event_type: Event, document_id: str):
    callback_options = ATTENDANCE_STATE_OPTIONS.copy()
    callback_options.append(CallbackOption.CALENDAR)
    return _get_reply_markup(callback_options, user_state, event_type, document_id)


def get_stats_event_reply_markup(user_state: UserState, event_type: Event, document_id: str):
    callback_options = [CallbackOption.CALENDAR]
    return _get_reply_markup(callback_options, user_state, event_type, document_id)


def get_update_or_delete_reply_markup(event_type: Event, document_id: str):
    return _get_reply_markup(UPDATE_OR_DELETE_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)


def get_yes_or_no_markup(event_type: Event, document_id: str):
    return _get_reply_markup(YES_OR_NO_OPTIONS, UserState.ADMIN_UPDATE, event_type, document_id)


def get_reset_statistics_markup():
    # A reset has no event/document, but the callback format requires both - the placeholders are
    # ignored by the reset callback node. ADMIN_STATISTICS (the screen the admin is on) routes the click.
    return _get_reply_markup(YES_OR_NO_OPTIONS, UserState.ADMIN_STATISTICS, Event.GAME, '')


def get_website_confirm_markup():
    # Plain yes/no confirm; the new URL itself is too long for callback_data (64-byte limit) and is
    # stashed in the user's state instead. ADMIN_UPDATE_WEBSITE (the screen the admin is on) routes the click.
    return _get_reply_markup(YES_OR_NO_OPTIONS, UserState.ADMIN_UPDATE_WEBSITE, Event.GAME, '')


def get_option_translation(option: CallbackOption):
    match option:
        case CallbackOption.CALENDAR:
            return 'export to calendar'
        case _:
            return option.name


def _get_reply_markup(options: [CallbackOption], user_state: UserState, event_type: Event, document_id: str):
    button_list = []
    for option in options:
        callback_data = get_callback_message(user_state, event_type, option, document_id)
        new_button = InlineKeyboardButton(get_option_translation(option), callback_data=callback_data)
        button_list.append(new_button)

    split_button_list = [button_list[i:i + 3] for i in range(0, len(button_list), 3)]  # max 3 items per row
    return InlineKeyboardMarkup(split_button_list)


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


class EventFieldEdit(NamedTuple):
    """The context for a single-field event edit, stashed in UsersToState.additional_info
    while the admin types the new value (the inline message to update, plus which event
    and field are being edited)."""
    message_id: int
    chat_id: int
    doc_id: str
    event_type: Event
    field: CallbackOption


def build_additional_information(message_id: int, chat_id: int, event_document_id: str, event_type: Event,
                                 field: CallbackOption) -> str:
    return DELIMITER.join([str(message_id), str(chat_id), event_document_id, str(int(event_type)), str(int(field))])


def try_parse_additional_information(message: str) -> EventFieldEdit | None:
    split = message.split(DELIMITER)
    if len(split) != 5:
        return None

    try:
        return EventFieldEdit(int(split[0]), int(split[1]), split[2], Event(int(split[3])),
                              CallbackOption(int(split[4])))
    except ValueError:
        return None
