"""RFC 5545 mechanics of the feed renderer: CRLF, folding by octets, TEXT escaping,
UTC stamps, fixed property order (plan §6 «Text», «Times»)."""
import re
from datetime import datetime, timezone

import pandas as pd
import pytest

from domain.calendar.CalendarFeed import FeedEntry, EVENT_DURATION
from domain.calendar.Ics import event_uid, render_calendar

NOW = datetime(2030, 1, 10, 8, 15, 0, tzinfo=timezone.utc)
HEADER = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//ZW Date Bot//Kalender-Abo//DE',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'X-WR-CALNAME:Züri West',
    'REFRESH-INTERVAL;VALUE=DURATION:PT6H',
    'X-PUBLISHED-TTL:PT6H',
]


def zurich(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz='Europe/Zurich')


def entry(summary='Handball Game Züri West (rivals fc)', start=None, location='Home Arena',
          description='Your answer: ✅ Yes', uid='game-1@zw-date-bot', status='CONFIRMED') -> FeedEntry:
    start = start if start is not None else zurich('2030-01-15 14:30')
    return FeedEntry(uid=uid, start=start, end=start + EVENT_DURATION, summary=summary,
                     status=status, location=location, description=description)


def physical_lines(ics: str) -> list[str]:
    assert ics.endswith('\r\n')
    return ics[:-2].split('\r\n')


def logical_lines(ics: str) -> list[str]:
    return physical_lines(ics.replace('\r\n ', ''))


def unescape_text(value: str) -> str:
    return re.sub(r'\\(.)', lambda match: '\n' if match.group(1) in 'nN' else match.group(1), value)


def property_value(ics: str, name: str) -> str:
    [value] = [line[len(name) + 1:] for line in logical_lines(ics) if line.startswith(f'{name}:')]
    return value


def test_every_line_ends_with_crlf_including_the_last_and_no_bare_line_breaks():
    ics = render_calendar([entry(summary='multi\nline\r\ntext\rhere')], 'Züri West', NOW)
    assert ics.endswith('END:VCALENDAR\r\n')
    without_crlf = ics.replace('\r\n', '')
    assert '\n' not in without_crlf
    assert '\r' not in without_crlf


def test_calendar_and_event_properties_in_fixed_order():
    ics = render_calendar([entry()], 'Züri West', NOW)
    assert logical_lines(ics) == HEADER + [
        'BEGIN:VEVENT',
        'UID:game-1@zw-date-bot',
        'DTSTAMP:20300110T081500Z',
        'DTSTART:20300115T133000Z',
        'DTEND:20300115T150000Z',
        'SUMMARY:Handball Game Züri West (rivals fc)',
        'STATUS:CONFIRMED',
        'LOCATION:Home Arena',
        'DESCRIPTION:Your answer: ✅ Yes',
        'END:VEVENT',
        'END:VCALENDAR',
    ]


def test_empty_entry_list_renders_a_valid_empty_calendar():
    ics = render_calendar([], 'Züri West', NOW)
    assert ics == '\r\n'.join(HEADER + ['END:VCALENDAR']) + '\r\n'


def test_location_and_description_are_left_out_when_unset():
    ics = render_calendar([entry(location=None, description=None)], 'Züri West', NOW)
    names = [line.split(':', 1)[0] for line in logical_lines(ics)]
    assert 'LOCATION' not in names
    assert 'DESCRIPTION' not in names


def test_no_alarm_and_no_url():
    ics = render_calendar([entry()], 'Züri West', NOW)
    assert 'VALARM' not in ics
    assert not any(line.startswith('URL') for line in logical_lines(ics))


def test_long_umlaut_line_is_folded_by_octets_never_splitting_a_character():
    summary = 'ü' * 60  # 120 octets
    ics = render_calendar([entry(summary=summary)], 'Züri West', NOW)

    lines = physical_lines(ics)
    for line in lines:
        assert len(line.encode('utf-8')) <= 75
    start = lines.index('SUMMARY:' + 'ü' * 33)  # 8 + 66 = 74: a 2-octet 'ü' no longer fits
    assert lines[start + 1] == ' ' + 'ü' * 27  # the rest: 1 + 54 octets
    assert property_value(ics, 'SUMMARY') == summary


def test_continuation_lines_carry_74_octets_after_their_space():
    summary = 'ü' * 80  # 8 + 160 octets: one full continuation line of 37 'ü'
    ics = render_calendar([entry(summary=summary)], 'Züri West', NOW)
    lines = physical_lines(ics)
    start = lines.index('SUMMARY:' + 'ü' * 33)
    assert lines[start + 1] == ' ' + 'ü' * 37
    assert len(lines[start + 1].encode('utf-8')) == 75
    assert lines[start + 2] == ' ' + 'ü' * 10
    assert property_value(ics, 'SUMMARY') == summary


@pytest.mark.parametrize('length, folded', [(75, False), (76, True)])
def test_fold_boundary_is_75_octets(length, folded):
    summary = 'x' * (length - len('SUMMARY:'))
    lines = physical_lines(render_calendar([entry(summary=summary)], 'Züri West', NOW))
    summary_index = next(i for i, line in enumerate(lines) if line.startswith('SUMMARY:'))
    assert lines[summary_index + 1].startswith(' ') is folded


def test_text_values_are_escaped_and_round_trip():
    tricky = 'a\\b;c,d\ne'
    ics = render_calendar([entry(summary=tricky, location=tricky, description=tricky)], tricky, NOW)
    assert property_value(ics, 'SUMMARY') == 'a\\\\b\\;c\\,d\\ne'
    for name in ('SUMMARY', 'LOCATION', 'DESCRIPTION', 'X-WR-CALNAME'):
        assert unescape_text(property_value(ics, name)) == tricky


def test_zurich_winter_and_summer_times_render_as_utc():
    winter = render_calendar([entry(start=zurich('2030-01-15 14:30'))], 'Züri West', NOW)
    summer = render_calendar([entry(start=zurich('2030-07-15 14:30'))], 'Züri West', NOW)
    assert property_value(winter, 'DTSTART') == '20300115T133000Z'
    assert property_value(summer, 'DTSTART') == '20300715T123000Z'
    assert property_value(summer, 'DTEND') == '20300715T140000Z'


def test_naive_times_are_rejected_instead_of_read_as_server_time():
    naive = FeedEntry(uid='x@zw-date-bot', start=datetime(2030, 1, 15, 14, 30), end=datetime(2030, 1, 15, 16, 0),
                      summary='s', status='CONFIRMED', location=None, description=None)
    with pytest.raises(ValueError):
        render_calendar([naive], 'Züri West', NOW)


def test_event_uid_is_stable_per_doc_id():
    assert event_uid('abc-123') == 'abc-123@zw-date-bot'
    assert event_uid('abc-123') == event_uid('abc-123')
    assert event_uid('abc-123') != event_uid('abc-124')


def test_control_characters_are_dropped_from_text_values():
    dirty = FeedEntry(uid='x@zw-date-bot', start=zurich('2030-01-15 14:30'), end=zurich('2030-01-15 16:00'),
                      summary='Spiel\x00 gegen\x07 X\x7f', status='CONFIRMED', location='Halle\x0b 1', description=None)
    rendered = render_calendar([dirty], 'Züri West', NOW)
    assert property_value(rendered, 'SUMMARY') == 'Spiel gegen X'
    assert property_value(rendered, 'LOCATION') == 'Halle 1'
