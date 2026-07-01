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

    ADMIN_UPDATE_EVENT_FIELD = 140

    ADMIN_STATISTICS = 130
    ADMIN_UPDATE_WEBSITE = 131

    REJECTED = 999

    @classmethod
    def _missing_(cls, value):
        # These enum values were removed when the add- and update-event field states were
        # collapsed (the field now lives in TempData.step / additional_info, not the enum).
        # Coerce a persisted legacy value to its surviving state so a user who was mid-flow
        # at deploy time reads back as a valid state instead of crashing on
        # UserState(int(state)). Returning None keeps genuinely unknown values a ValueError.
        return _LEGACY_STATES.get(value)


# Legacy persisted UserState ints -> the surviving state. Removed add-event field states
# map to their per-type parent; removed update-event field states map to the update menu
# (their legacy additional_info can't resume the edit, so they re-navigate from there).
_LEGACY_STATES = {
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
    100: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_GAME_LOCATION
    101: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_GAME_OPPONENT
    102: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_GAME_TIMESTAMP
    110: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_TRAINING_LOCATION
    112: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_TRAINING_TIMESTAMP
    120: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_TIMEKEEPING_LOCATION
    122: UserState.ADMIN_UPDATE,          # ADMIN_UPDATE_TIMEKEEPING_TIMESTAMP
}
