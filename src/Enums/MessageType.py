from enum import IntEnum


class MessageType(IntEnum):
    ERROR = -1

    WRONG_START_COMMAND = 1
    WELCOME = 2
    WEBSITE = 5
    PRIVACY = 6

    EVENT_TIMESTAMP_CHANGED = 110
    EVENT_ADDED = 111

    ENROLLMENT_REMINDER = 300

    REJECTED = 999
