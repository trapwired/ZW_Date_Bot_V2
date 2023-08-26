from Enums.UserState import UserState

from Enums.AttendanceState import AttendanceState

DELIMITER = '-'


def get_callback_message(user_state: UserState, option: AttendanceState, doc_id: str):
    return user_state.name + DELIMITER + option.name + DELIMITER + doc_id


def try_parse_callback_message(message: str) -> tuple[UserState, AttendanceState, str] | None:
    split = message.split(DELIMITER)
    if len(split) != 3:
        return None

    try:
        user_state = UserState[split[0]]
        attendance_state = AttendanceState[split[1]]
        doc_id = split[2]
    except KeyError:
        return None

    return user_state, attendance_state, doc_id
