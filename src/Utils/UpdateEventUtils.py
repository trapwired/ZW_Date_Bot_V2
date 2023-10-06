from src.Enums.CallbackOption import CallbackOption
from src.Enums.Event import Event


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