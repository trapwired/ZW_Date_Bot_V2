import datetime

import pytz
from Enums.CallbackOption import CallbackOption
from Enums.Event import Event

from databaseEntities.Game import Game
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training

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


def get_inline_message(prefix_string: str, event_type: Event, event: Game | Training | TimekeepingEvent, middle_string: str = '') -> str:
    event_type_string = event_type.name.lower().title()

    match event_type:
        case Event.GAME:
            event_summary = PrintUtils.pretty_print_long(event)
        case Event.TRAINING:
            event_summary = PrintUtils.pretty_print(event)
        case Event.TIMEKEEPING:
            event_summary = PrintUtils.pretty_print(event)
    return f'{prefix_string} {event_type_string} {middle_string}: {event_summary}'


def parse_datetime_string(datetime_string: str):
    # Parse 20.03.2023 19:38 into datetime
    datetime_string = datetime_string.strip()
    split = datetime_string.split(" ")
    if len(split) != 2:
        return 'Tried to split into date and time by space in middle, this did not work - please try again'

    date = split[0].strip()
    time = split[1].strip()
    date_split_separators = '.,-'
    date_split = date.split(date_split_separators)
    if len(date_split) != 3:
        return (f'Tried to split date ({date}) into 3 parts, using the following separators: ({date_split_separators}) '
                f'- that did not work - wrong length: {len(date_split)}')
    month_str = date_split[0]
    day_str = date_split[1]
    year_str = date_split[2]
    try:
        month = int(month_str)
        day = int(day_str)
        year = int(year_str)
    except Exception as e:
        return (f'Tried to parse month / day / year into a number - that did not work, please try again (Exception for '
                f'reference: : {e.args})')

    time_split_separators = '-:;'
    time_split = time.split(time_split_separators)
    if len(time_split) != 2:
        return (f'Tried to split time ({time}) into 3 parts, using the following separators: ({time_split_separators}) '
                f'- that did not work - wrong length: {len(time_split)}')

    hour_str = time_split[0]
    min_str = time_split[1]
    try:
        hour = int(hour_str)
        minute = int(min_str)
    except Exception as e:
        return (f'Tried to parse hour / minute into a number - that did not work, please try again (Exception for '
                f'reference: : {e.args})')

    return datetime.datetime(year, month, day, hour, minute, 0, 0, tzinfo=pytz.timezone('Europe/Zurich'))
