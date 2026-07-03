"""Pins the spectator-password brute-force policy: N failures per rolling window,
self-healing decode, and the exactly-once lockout signal."""
from datetime import datetime, timedelta

from domain import SpectatorPasswordPolicy as policy

NOW = datetime(2026, 7, 3, 20, 0)


def _failed(times: int, start: datetime = NOW):
    record = None
    for i in range(times):
        record = policy.register_failure(record, start + timedelta(minutes=i))
    return record


def test_unparseable_or_empty_records_count_as_clean():
    for garbage in ('', 'https://stale.example', 'pw_attempts#x#y', None):
        assert policy.decode(garbage or '') is None
    assert policy.is_locked(None, NOW) is False


def test_encode_decode_roundtrip():
    record = _failed(3)
    assert policy.decode(policy.encode(record)) == record


def test_locks_at_threshold_and_signals_exactly_once():
    record = _failed(policy.MAX_FAILED_ATTEMPTS - 1)
    assert policy.is_locked(record, NOW + timedelta(minutes=10)) is False
    assert policy.just_reached_lockout(record) is False

    record = policy.register_failure(record, NOW + timedelta(minutes=10))
    assert policy.is_locked(record, NOW + timedelta(minutes=11)) is True
    assert policy.just_reached_lockout(record) is True

    record = policy.register_failure(record, NOW + timedelta(minutes=12))
    assert policy.just_reached_lockout(record) is False   # alert only on the crossing


def test_window_expiry_unlocks_and_restarts_the_count():
    record = _failed(policy.MAX_FAILED_ATTEMPTS)
    after_window = NOW + policy.ATTEMPT_WINDOW + timedelta(minutes=1)
    assert policy.is_locked(record, after_window) is False
    fresh = policy.register_failure(record, after_window)
    assert fresh.failed_count == 1
    assert fresh.window_start == after_window
