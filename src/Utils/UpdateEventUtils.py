from Enums.EventField import EventField
from Enums.Event import Event

from domain.entities.Game import Game
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training

from Utils import PrintUtils


def get_input_format_string(callback_option: EventField):
    match callback_option:
        case EventField.OPPONENT:
            return 'freetext, spaces allowed, no max length, but end will be trimmed'
        case EventField.LOCATION:
            return 'freetext, spaces allowed, no max length, but end will be trimmed'
        case EventField.DATETIME:
            return 'numbers and symbols, format: 20.03.2023 19:38'


def get_inline_message(prefix_string: str, event_type: Event, event: Game | Training | TimekeepingEvent | str,
                       middle_string: str = '') -> str:
    event_type_string = PrintUtils.event_label(event_type)

    if type(event) is str:
        event_summary = event
    else:
        match event_type:
            case Event.GAME:
                event_summary = PrintUtils.pretty_print_long(event)
            case Event.TRAINING:
                event_summary = PrintUtils.pretty_print(event)
            case Event.TIMEKEEPING:
                event_summary = PrintUtils.pretty_print(event)
    return f'{prefix_string} {event_type_string} {middle_string}: {event_summary}'


