from enum import IntEnum


class UserState(IntEnum):
    INIT = -1
    DEFAULT = 0

    STATS = 1
    STATS_TIMEKEEPINGS = 2
    STATS_TRAININGS = 3
    STATS_GAMES = 4

    EDIT = 10
    EDIT_TIMEKEEPINGS = 11
    EDIT_TRAININGS = 12
    EDIT_GAMES = 13

    ADMIN = 50
    ADMIN_ADD = 51
    ADMIN_UPDATE = 52
    ADMIN_UPDATE_GAME = 53
    ADMIN_UPDATE_TRAINING = 54
    ADMIN_UPDATE_TIMEKEEPING = 55
    ADMIN_ADD_GAME = 56
    ADMIN_ADD_TRAINING = 57
    ADMIN_ADD_TIMEKEEPING = 58

    ADMIN_UPDATE_GAME_LOCATION = 100
    ADMIN_UPDATE_GAME_OPPONENT = 101
    ADMIN_UPDATE_GAME_TIMESTAMP = 102

    ADMIN_UPDATE_TRAINING_LOCATION = 110
    ADMIN_UPDATE_TRAINING_TIMESTAMP = 112

    ADMIN_UPDATE_TIMEKEEPING_LOCATION = 120
    ADMIN_UPDATE_TIMEKEEPING_TIMESTAMP = 122

    ADMIN_STATISTICS = 130
    ADMIN_UPDATE_WEBSITE = 131

    REJECTED = 999

    @classmethod
    def _missing_(cls, value):
        # Phase 3a collapsed the per-field add-event states into the per-type parent and
        # moved the step into TempData.step. Coerce any persisted pre-3a value so a user
        # who was mid-wizard at deploy time reads back as the parent state instead of
        # crashing on UserState(int(state)). Returning None keeps genuinely unknown values
        # a ValueError.
        return _LEGACY_ADD_STATES.get(value)


_LEGACY_ADD_STATES = {
    103: UserState.ADMIN_ADD_GAME,        # ADMIN_ADD_GAME_TIMESTAMP
    104: UserState.ADMIN_ADD_GAME,        # ADMIN_ADD_GAME_LOCATION
    105: UserState.ADMIN_ADD_GAME,        # ADMIN_ADD_GAME_OPPONENT
    106: UserState.ADMIN_ADD_GAME,        # ADMIN_FINISH_ADD_GAME
    113: UserState.ADMIN_ADD_TRAINING,    # ADMIN_ADD_TRAINING_LOCATION
    114: UserState.ADMIN_ADD_TRAINING,    # ADMIN_ADD_TRAINING_TIMESTAMP
    115: UserState.ADMIN_ADD_TRAINING,    # ADMIN_FINISH_ADD_TRAINING
    123: UserState.ADMIN_ADD_TIMEKEEPING,  # ADMIN_ADD_TIMEKEEPING_LOCATION
    124: UserState.ADMIN_ADD_TIMEKEEPING,  # ADMIN_ADD_TIMEKEEPING_TIMESTAMP
    125: UserState.ADMIN_ADD_TIMEKEEPING,  # ADMIN_FINISH_ADD_TIMEKEEPING
}
