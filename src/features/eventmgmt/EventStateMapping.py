"""Single source for the add-event wizard's per-type UserState.

Three call sites need the ADMIN_ADD_<type> state for an event type (draft markup,
the admin-add entry point, and the add callback's SAVE branch); keeping the map here
stops those copies from drifting apart.
"""
from Enums.Event import Event
from Enums.UserState import UserState

ADD_EVENT_USER_STATE = {
    Event.GAME: UserState.ADMIN_ADD_GAME,
    Event.TRAINING: UserState.ADMIN_ADD_TRAINING,
    Event.TIMEKEEPING: UserState.ADMIN_ADD_TIMEKEEPING,
}


def add_event_user_state(event_type: Event) -> UserState:
    try:
        return ADD_EVENT_USER_STATE[event_type]
    except KeyError:
        raise ValueError(f'No add-event UserState for event type: {event_type}')
