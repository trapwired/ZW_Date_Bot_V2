"""Unit tests for the event datetime parser (moved to domain in Phase 2).

The old str-or-value contract is gone: parse() now returns a ParsedDateTime with
.ok / .value / .error.
"""
import pandas as pd

from domain.EventDateTimeParser import parse


def _assert_ok(result, expected):
    assert result.ok
    assert result.error is None
    assert isinstance(result.value, pd.Timestamp)
    assert result.value.tzinfo is not None  # add_zurich_timezone attaches a tz
    assert (result.value.year, result.value.month, result.value.day,
            result.value.hour, result.value.minute) == expected


def test_parses_canonical_format():
    _assert_ok(parse("24.12.2030 18:30"), (2030, 12, 24, 18, 30))


def test_accepts_alternate_separators():
    # date separators are '.,-', time separators are '-:;'
    _assert_ok(parse("24-12-2030 18-30"), (2030, 12, 24, 18, 30))
    _assert_ok(parse("24,12,2030 18;30"), (2030, 12, 24, 18, 30))


def test_collapses_repeated_whitespace_between_date_and_time():
    _assert_ok(parse("24.12.2030    18:30"), (2030, 12, 24, 18, 30))
    _assert_ok(parse("  24.12.2030\t18:30  "), (2030, 12, 24, 18, 30))


def test_errors_report_not_ok_with_a_message():
    for bad in ("not a date", "24.12.2030", "1.2.3.4 5:6", "24.12.2030 xx:30"):
        result = parse(bad)
        assert not result.ok
        assert result.value is None
        assert isinstance(result.error, str) and result.error


def test_numeric_but_invalid_calendar_values_fail_instead_of_crashing():
    # Each parses as ints but is not a real date/time; must return a failure, not raise.
    for bad in ("32.12.2030 18:30", "24.13.2030 18:30", "24.12.2030 25:30", "24.12.2030 18:61"):
        result = parse(bad)
        assert not result.ok
        assert result.value is None
        assert isinstance(result.error, str) and result.error
