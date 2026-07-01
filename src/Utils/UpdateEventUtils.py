from Enums.CallbackOption import CallbackOption
from Enums.Event import Event

from domain.entities.Game import Game
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training

from Utils import PrintUtils


def mark_updating_in_event_string(event_type: Event, event_summary: str, option: CallbackOption):
    split = event_summary.split('|')
    match event_type:
        case Event.GAME:
            match option:
                case option.OPPONENT:
                    split[2] = 'UPDATING'
                case option.LOCATION:
                    split[1] = 'UPDATING'
                case option.DATETIME:
                    split[0] = 'UPDATING'
        case Event.TRAINING:
            match option:
                case option.LOCATION:
                    split[1] = 'UPDATING'
                case option.DATETIME:
                    split[0] = 'UPDATING'
        case Event.TIMEKEEPING:
            match option:
                case option.LOCATION:
                    split[1] = 'UPDATING'
                case option.DATETIME:
                    split[0] = 'UPDATING'
    return ' | '.join(split)


def get_input_format_string(callback_option: CallbackOption):
    match callback_option:
        case CallbackOption.OPPONENT:
            return 'freetext, spaces allowed, no max length, but end will be trimmed'
        case CallbackOption.LOCATION:
            return 'freetext, spaces allowed, no max length, but end will be trimmed'
        case CallbackOption.DATETIME:
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


