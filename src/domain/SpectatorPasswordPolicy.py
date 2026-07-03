"""Brute-force guard for spectator-password attempts.

The spectator password is a shared, human-chosen secret, so the only defense against
someone guessing their way into a team is throttling: a user may fail
MAX_FAILED_ATTEMPTS times per rolling window, then the REJECTED screen stops
evaluating their guesses until the window has passed.

The attempt record rides in the rejected user's UsersToState.additional_info (unused
in that state). Anything unparseable - legacy values, empty - counts as a clean
record, so the guard self-heals on read (ADR 0002 style).
"""
from datetime import datetime, timedelta
from typing import NamedTuple

MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW = timedelta(hours=24)

_PREFIX = 'pw_attempts'
_DELIMITER = '#'


class AttemptRecord(NamedTuple):
    failed_count: int
    window_start: datetime


def decode(additional_info: str) -> AttemptRecord | None:
    parts = (additional_info or '').split(_DELIMITER)
    if len(parts) != 3 or parts[0] != _PREFIX:
        return None
    try:
        return AttemptRecord(int(parts[1]), datetime.fromisoformat(parts[2]))
    except ValueError:
        return None


def encode(record: AttemptRecord) -> str:
    return _DELIMITER.join([_PREFIX, str(record.failed_count), record.window_start.isoformat()])


def _window_expired(record: AttemptRecord, now: datetime) -> bool:
    return now - record.window_start >= ATTEMPT_WINDOW


def register_failure(record: AttemptRecord | None, now: datetime) -> AttemptRecord:
    if record is None or _window_expired(record, now):
        return AttemptRecord(1, now)
    return AttemptRecord(record.failed_count + 1, record.window_start)


def is_locked(record: AttemptRecord | None, now: datetime) -> bool:
    if record is None or _window_expired(record, now):
        return False
    return record.failed_count >= MAX_FAILED_ATTEMPTS


def just_reached_lockout(record: AttemptRecord) -> bool:
    """True exactly once per window - the moment to alert the maintainer."""
    return record.failed_count == MAX_FAILED_ATTEMPTS
