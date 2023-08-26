from Enums.UserState import UserState

DELIMITER = '-'


def get_callback_message(user_state: UserState, option: str, doc_id: str):
    return str(user_state) + DELIMITER + option + DELIMITER + doc_id
