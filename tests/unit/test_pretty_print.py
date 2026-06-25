"""Pin the per-event renderers Phase 1 de-triplicates.

Expected values are composed from the real Format helpers so the test pins the
COMPOSITION ('bold(datetime) | escape(location)' etc.), staying robust to the
exact HTML dialect while still catching a structural regression.
"""
import pandas as pd

from databaseEntities.Game import Game
from databaseEntities.Training import Training
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from Enums.AttendanceState import AttendanceState
from Utils import Format
from Utils import PrintUtils

# Entities convert via astimezone, so the input must be tz-aware. Expected values
# are derived from the stored timestamp, so the tz shift doesn't affect the pins.
TS = pd.Timestamp("2030-12-24 18:30", tz="UTC")


def _dt(event):
    return event.timestamp.strftime(PrintUtils.DATETIME_FORMAT)


def test_pretty_print_game_single_line():
    game = Game(TS, "home arena", "rivals fc")
    assert PrintUtils.pretty_print(game) == f"{Format.bold(_dt(game))} | {Format.escape('Home Arena')}"


def test_pretty_print_game_long_adds_opponent():
    game = Game(TS, "home arena", "rivals fc")
    assert PrintUtils.pretty_print_long(game) == f"{PrintUtils.pretty_print(game)} | {Format.escape('Rivals Fc')}"


def test_pretty_print_training_single_line():
    training = Training(TS, "sporthalle")
    assert PrintUtils.pretty_print(training) == f"{Format.bold(_dt(training))} | {Format.escape('Sporthalle')}"


def test_pretty_print_timekeeping_single_line():
    tke = TimekeepingEvent(TS, "eventhalle")
    assert PrintUtils.pretty_print(tke) == f"{Format.bold(_dt(tke))} | {Format.escape('Eventhalle')}"


def test_pretty_print_with_attendance_state_appends_state():
    game = Game(TS, "home arena", "rivals fc")
    rendered = PrintUtils.pretty_print(game, AttendanceState.YES)
    assert rendered.startswith(PrintUtils.pretty_print(game) + " | ")
    assert "Yes" in rendered


def test_event_command_is_plain_text_for_matching():
    # Reply-keyboard label + matching command: must stay plain (no HTML), exact format.
    game = Game(TS, "home arena", "rivals fc")
    assert PrintUtils.pretty_print_event_command(game) == f"{_dt(game)} | Home Arena"
