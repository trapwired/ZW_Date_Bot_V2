from enum import IntEnum


class UserState(IntEnum):
    INIT = -1
    DEFAULT = 0

    STATS = 1
    STATS_TIMEKEEPINGS = 2
    STATS_TRAININGS = 3
    STATS_GAMES = 4

    EDIT = 10

    REJECTED = 999
