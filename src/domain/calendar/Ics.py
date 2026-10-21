"""RFC 5545 renderer for the subscribed calendar feed: one VCALENDAR, UTC times,
TEXT escaping, lines folded by octets, CRLF after every line. Hand-rolled because
the `ics` lib neither folds nor orders events stably (plan §2)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.calendar.CalendarFeed import FeedEntry

UID_DOMAIN = 'zw-date-bot'
PRODUCT_ID = '-//ZW Date Bot//Kalender-Abo//DE'
REFRESH_INTERVAL = 'PT6H'  # a hint only; Google polls every 12-24 h regardless

CRLF = '\r\n'
MAX_LINE_OCTETS = 75

_LINE_BREAK = re.compile(r'\r\n|\r|\n')
# RFC 5545 TEXT allows no C0 control character except TAB (and no DEL); strict parsers reject the file.
_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def event_uid(doc_id: str) -> str:
    return f'{doc_id}@{UID_DOMAIN}'


def render_calendar(entries: list[FeedEntry], calendar_name: str, now: datetime) -> str:
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:{PRODUCT_ID}',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_escape_text(calendar_name)}',
        f'REFRESH-INTERVAL;VALUE=DURATION:{REFRESH_INTERVAL}',
        f'X-PUBLISHED-TTL:{REFRESH_INTERVAL}',
    ]
    for entry in entries:
        lines += [
            'BEGIN:VEVENT',
            f'UID:{entry.uid}',
            f'DTSTAMP:{_utc_stamp(now)}',
            f'DTSTART:{_utc_stamp(entry.start)}',
            f'DTEND:{_utc_stamp(entry.end)}',
            f'SUMMARY:{_escape_text(entry.summary)}',
            f'STATUS:{entry.status}',
        ]
        if entry.location:
            lines.append(f'LOCATION:{_escape_text(entry.location)}')
        if entry.description:
            lines.append(f'DESCRIPTION:{_escape_text(entry.description)}')
        lines.append('END:VEVENT')
    lines.append('END:VCALENDAR')
    return ''.join(_fold(line) + CRLF for line in lines)


def _utc_stamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        # A naive time would silently be read as the server's local time.
        raise ValueError(f'calendar times must be timezone-aware, got {moment!r}')
    return moment.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _escape_text(text: str) -> str:
    text = _CONTROL_CHARS.sub('', text)
    # Backslash first, or the escapes added below would be doubled.
    escaped = text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
    return _LINE_BREAK.sub(r'\\n', escaped)


def _fold(line: str) -> str:
    # Never splits a character; a continuation line's leading space counts towards its 75.
    parts = []
    current = ''
    octets = 0
    for char in line:
        size = len(char.encode('utf-8'))
        limit = MAX_LINE_OCTETS if not parts else MAX_LINE_OCTETS - 1
        if octets + size > limit:
            parts.append(current)
            current = ''
            octets = 0
        current += char
        octets += size
    parts.append(current)
    return (CRLF + ' ').join(parts)
