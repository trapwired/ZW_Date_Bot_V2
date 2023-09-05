from enum import IntEnum


class MessageType(IntEnum):
    ERROR = -1

    HELP = 0
    WRONG_START_COMMAND = 1
    WELCOME = 2
    TO_STATS = 3
    TO_EDIT = 4
    WEBSITE = 5

    STATS_TO_GAMES = 10
    STATS_TO_TRAININGS = 11
    STATS_TO_TIMEKEEPINGS = 12
    STATS_OVERVIEW = 13

    EDIT_TO_GAMES = 20
    EDIT_TO_TRAININGS = 21
    EDIT_TO_TIMEKEEPINGS = 22
    EDIT_OVERVIEW = 23

    CONTINUE_LATER = 42
    UNKNOWN_COMMAND = 43

    ADD = 50
    UPDATE = 51

    REJECTED = 999
