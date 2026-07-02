from enum import IntEnum


class UserState(IntEnum):
    """Which node routes a user's next text message. Since the menu redesign the bot is
    inline-first: DEFAULT is the only menu state, the remaining states exist solely to
    capture typed input (wizard values, a field edit, a URL)."""
    INIT = -1
    DEFAULT = 0

    ADMIN_ADD_EVENT = 60

    ADMIN_UPDATE_WEBSITE = 131
    ADMIN_UPDATE_EVENT_FIELD = 140

    REJECTED = 999

    @classmethod
    def _missing_(cls, value):
        # Persisted states from before the menu redesign (and the earlier wizard-state
        # collapse) resolve to a surviving state instead of crashing on
        # UserState(int(state)). Returning None from _missing_ makes a genuinely
        # unknown value raise ValueError, as usual.
        return _LEGACY_STATES.get(value)


# Legacy persisted UserState ints -> the surviving state.
# - Old menu screens (stats/edit/admin navigation) all collapse into the main menu.
# - Old per-type add-wizard states collapse into ADMIN_ADD_EVENT (the draft carries the
#   event type, so an in-flight wizard resumes where it left off).
# - Old update-field states can't resume their edit; they land on the main menu.
_LEGACY_STATES = {
    1: UserState.DEFAULT,    # STATS
    2: UserState.DEFAULT,    # STATS_TIMEKEEPINGS
    3: UserState.DEFAULT,    # STATS_TRAININGS
    4: UserState.DEFAULT,    # STATS_GAMES
    10: UserState.DEFAULT,   # EDIT
    11: UserState.DEFAULT,   # EDIT_TIMEKEEPINGS
    12: UserState.DEFAULT,   # EDIT_TRAININGS
    13: UserState.DEFAULT,   # EDIT_GAMES
    50: UserState.DEFAULT,   # ADMIN
    51: UserState.DEFAULT,   # ADMIN_ADD
    52: UserState.DEFAULT,   # ADMIN_UPDATE
    53: UserState.DEFAULT,   # ADMIN_UPDATE_GAME
    54: UserState.DEFAULT,   # ADMIN_UPDATE_TRAINING
    55: UserState.DEFAULT,   # ADMIN_UPDATE_TIMEKEEPING
    130: UserState.DEFAULT,  # ADMIN_STATISTICS

    56: UserState.ADMIN_ADD_EVENT,   # ADMIN_ADD_GAME
    57: UserState.ADMIN_ADD_EVENT,   # ADMIN_ADD_TRAINING
    58: UserState.ADMIN_ADD_EVENT,   # ADMIN_ADD_TIMEKEEPING
    103: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_GAME_TIMESTAMP
    104: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_GAME_LOCATION
    105: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_GAME_OPPONENT
    106: UserState.ADMIN_ADD_EVENT,  # ADMIN_FINISH_ADD_GAME
    113: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_TRAINING_LOCATION
    114: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_TRAINING_TIMESTAMP
    115: UserState.ADMIN_ADD_EVENT,  # ADMIN_FINISH_ADD_TRAINING
    123: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_TIMEKEEPING_LOCATION
    124: UserState.ADMIN_ADD_EVENT,  # ADMIN_ADD_TIMEKEEPING_TIMESTAMP
    125: UserState.ADMIN_ADD_EVENT,  # ADMIN_FINISH_ADD_TIMEKEEPING

    100: UserState.DEFAULT,  # ADMIN_UPDATE_GAME_LOCATION
    101: UserState.DEFAULT,  # ADMIN_UPDATE_GAME_OPPONENT
    102: UserState.DEFAULT,  # ADMIN_UPDATE_GAME_TIMESTAMP
    110: UserState.DEFAULT,  # ADMIN_UPDATE_TRAINING_LOCATION
    112: UserState.DEFAULT,  # ADMIN_UPDATE_TRAINING_TIMESTAMP
    120: UserState.DEFAULT,  # ADMIN_UPDATE_TIMEKEEPING_LOCATION
    122: UserState.DEFAULT,  # ADMIN_UPDATE_TIMEKEEPING_TIMESTAMP
}
