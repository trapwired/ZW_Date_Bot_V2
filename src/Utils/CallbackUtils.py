from Enums.UserState import UserState

DELIMITER = '-'


def get_callback_message(user_state: UserState, option: str, doc_id: str):
    return user_state.name + DELIMITER + option + DELIMITER + doc_id


def try_parse_callback_message(message: str) -> tuple[UserState, str, str] | None:
    split = message.split(DELIMITER)
    if len(split) != 3:
        return None
