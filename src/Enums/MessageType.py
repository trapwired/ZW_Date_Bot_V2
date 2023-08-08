from enum import IntEnum


class MessageType(IntEnum):
    ERROR = -1

    HELP = 0
    WRONG_START_COMMAND = 1
    WELCOME = 2

    CONTINUE_LATER = 42

