from enum import IntEnum


class EventField(IntEnum):
    """An editable field of an event. Doubles as the add-event wizard's step marker
    (TempData.step), where SAVE is the pseudo-step after the last field.

    Values are persisted (TempData.step, UsersToState.additional_info) and predate the
    rename from CallbackOption - keep them stable."""
    LOCATION = 20
    OPPONENT = 21
    DATETIME = 22

    SAVE = 42
