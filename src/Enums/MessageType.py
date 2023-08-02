from enum import IntEnum


class MessageType(IntEnum):
    HELP = 0
    WRONG_START_COMMAND = 1
    WELCOME = 2

