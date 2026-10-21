"""Which event types a member may see, by membership role. The one rule for every
reader of the schedule (events menu, calendar feed): a second copy would drift."""
from Enums.Event import Event
from Enums.Role import Role

EVENT_TYPES_IN_ORDER = [Event.GAME, Event.TRAINING, Event.TIMEKEEPING]


def visible_event_types(role: Role) -> list[Event]:
    # Timekeeping duties are deliberately hidden from spectators.
    return [event_type for event_type in EVENT_TYPES_IN_ORDER
            if not (role is Role.SPECTATOR and event_type is Event.TIMEKEEPING)]
