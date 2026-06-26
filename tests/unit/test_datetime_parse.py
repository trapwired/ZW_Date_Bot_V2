"""Unit tests for the event datetime parser (moved to domain in Phase 2).

The old str-or-value contract is gone: parse() now returns a ParsedDateTime with
.ok / .value / .error.
"""
import pandas as pd

from domain.EventDateTimeParser import parse, parse_future


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


def test_two_digit_year_is_interpreted_as_20xx():
    _assert_ok(parse("1.1.30 15:15"), (2030, 1, 1, 15, 15))


def test_dot_is_accepted_as_time_separator():
    _assert_ok(parse("24.12.2030 14.14"), (2030, 12, 24, 14, 14))


def test_dst_nonexistent_time_fails_instead_of_crashing():
    # Europe/Zurich spring-forward 2023-03-26: 02:00 jumps to 03:00, so 02:30 does not exist.
    result = parse("26.3.2023 02:30")
    assert not result.ok
    assert result.value is None


def test_parse_future_rejects_past_and_accepts_future():
    assert not parse_future("1.1.2020 12:00").ok          # clearly past
    assert not parse_future("1.1.20 12:00").ok            # 2020 via two-digit year, still past
    assert parse_future("1.1.2099 12:00").ok              # clearly future
