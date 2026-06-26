"""Parsing of user-entered event date/times — domain logic, no Telegram/Firebase.

Returns an explicit ParsedDateTime result instead of the old str-or-Timestamp
union, so callers branch on `.ok` rather than `type(x) is str`.
"""
import pandas as pd

from Utils import DateTimeUtils

DATE_SEPARATORS = '.,-'
TIME_SEPARATORS = '-:;'
INPUT_FORMAT_HINT = '20.03.2023 19:38'


class ParsedDateTime:
    def __init__(self, value: pd.Timestamp | None, error: str | None):
        self.value = value
        self.error = error

    @property
    def ok(self) -> bool:
        return self.error is None

    @classmethod
    def success(cls, value: pd.Timestamp) -> "ParsedDateTime":
        return cls(value, None)

    @classmethod
    def failure(cls, error: str) -> "ParsedDateTime":
        return cls(None, error)


def _split_multiple(string: str, delimiters: str) -> list[str]:
    result = string
    for delimiter in delimiters:
        result = ' '.join(result.split(delimiter))
    return result.split()


def parse(datetime_string: str) -> ParsedDateTime:
    # Expected form: 20.03.2023 19:38
    # split() (no arg) collapses runs of whitespace, so 'date   time' or tabs still parse.
    split = datetime_string.split()
    if len(split) != 2:
        return ParsedDateTime.failure(
            'Tried to split into date and time by space in middle, this did not work - please try again')

    date, time = split[0].strip(), split[1].strip()

    date_split = _split_multiple(date, DATE_SEPARATORS)
    if len(date_split) != 3:
        return ParsedDateTime.failure(
            f'Tried to split date ({date}) into 3 parts, using the following separators: ({DATE_SEPARATORS}) '
            f'- that did not work - wrong length: {len(date_split)}')
    day_str, month_str, year_str = date_split
    try:
        day, month, year = int(day_str), int(month_str), int(year_str)
    except Exception as e:
        return ParsedDateTime.failure(
            f'Tried to parse month / day / year into a number - that did not work, please try again (Exception for '
            f'reference: : {e.args})')

    time_split = _split_multiple(time, TIME_SEPARATORS)
    if len(time_split) != 2:
        return ParsedDateTime.failure(
            f'Tried to split time ({time}) into 2 parts (hour and minute), using the following separators: '
            f'({TIME_SEPARATORS}) - that did not work - wrong length: {len(time_split)}')
    hour_str, min_str = time_split
    try:
        hour, minute = int(hour_str), int(min_str)
    except Exception as e:
        return ParsedDateTime.failure(
            f'Tried to parse hour / minute into a number - that did not work, please try again (Exception for '
            f'reference: : {e.args})')

    # The numbers parsed but may not form a real date/time (month 13, day 32, hour 25, ...).
    # pd.Timestamp raises on those; turn it into a failure result so the flow never crashes.
    try:
        date_time = pd.Timestamp(year, month, day, hour, minute, 0, 0)
    except (ValueError, OverflowError) as e:
        return ParsedDateTime.failure(
            f'That date/time does not exist, please try again (Exception for reference: {e.args})')
    return ParsedDateTime.success(DateTimeUtils.add_zurich_timezone(date_time))
