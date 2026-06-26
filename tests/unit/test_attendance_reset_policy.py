"""Unit pin for the attendance-reset domain rule extracted in Phase 2."""
import pandas as pd

from domain.AttendanceResetPolicy import requires_attendance_reset

BASE = pd.Timestamp("2030-12-24 18:30", tz="UTC")


def test_move_beyond_two_hours_requires_reset():
    assert requires_attendance_reset(BASE, BASE + pd.Timedelta(hours=2, minutes=1)) is True
    assert requires_attendance_reset(BASE, BASE - pd.Timedelta(hours=3)) is True


def test_move_within_two_hours_keeps_attendance():
    assert requires_attendance_reset(BASE, BASE + pd.Timedelta(hours=2)) is False
    assert requires_attendance_reset(BASE, BASE + pd.Timedelta(minutes=30)) is False
    assert requires_attendance_reset(BASE, BASE) is False
