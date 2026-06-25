"""Pin parse_datetime_string before Phase 2 moves it into the domain layer.

Pins the current contract INCLUDING its quirk: errors are returned as plain
strings (not raised). Phase 2 replaces that str-or-value union with a result
object, so this test should flip intentionally then.
"""
import pandas as pd

from Utils.UpdateEventUtils import parse_datetime_string


def _assert_parsed(result, expected):
    assert isinstance(result, pd.Timestamp)
    assert result.tzinfo is not None  # add_zurich_timezone attaches a tz
    assert (result.year, result.month, result.day, result.hour, result.minute) == expected


def test_parses_canonical_format():
    _assert_parsed(parse_datetime_string("24.12.2030 18:30"), (2030, 12, 24, 18, 30))


def test_accepts_alternate_separators():
    # date separators are '.,-', time separators are '-:;'
    _assert_parsed(parse_datetime_string("24-12-2030 18-30"), (2030, 12, 24, 18, 30))
    _assert_parsed(parse_datetime_string("24,12,2030 18;30"), (2030, 12, 24, 18, 30))


def test_errors_are_returned_as_strings_not_raised():
    assert isinstance(parse_datetime_string("not a date"), str)
    assert isinstance(parse_datetime_string("24.12.2030"), str)        # missing time half
    assert isinstance(parse_datetime_string("1.2.3.4 5:6"), str)       # date has 4 parts
    assert isinstance(parse_datetime_string("24.12.2030 xx:30"), str)  # non-numeric time
