"""Unit: backward-compat for removed UserStates.

A user parked on a pre-redesign menu screen (or mid-wizard) at deploy time carries a
legacy persisted state value. Reading it back must not crash and must land them on a
state that still exists.
"""
import pandas as pd
import pytest

from Enums.EventField import EventField
from Enums.Event import Event
from Enums.UserState import UserState
from domain.entities.TempData import TempData

# Persisted timestamps come back as tz-aware pd.Timestamp objects, not strings.
TS = pd.Timestamp("2030-12-24 18:30", tz="UTC")


# --- UserState._missing_: legacy ints coerce to a surviving state ---

@pytest.mark.parametrize("legacy_value", [
    1, 2, 3, 4,          # STATS menu family
    10, 11, 12, 13,      # EDIT menu family
    50, 51, 52,          # ADMIN / ADMIN_ADD / ADMIN_UPDATE
    53, 54, 55,          # ADMIN_UPDATE_<type> pickers
    130,                 # ADMIN_STATISTICS
    100, 101, 102, 110, 112, 120, 122,  # ancient per-field update states
])
def test_legacy_menu_state_int_coerces_to_main_menu(legacy_value):
    assert UserState(legacy_value) is UserState.DEFAULT


@pytest.mark.parametrize("legacy_value", [
    56, 57, 58,                      # ADMIN_ADD_<type> wizard states
    103, 104, 105, 106,              # ancient add-game field states
    113, 114, 115, 123, 124, 125,    # ancient add-training/-timekeeping field states
])
def test_legacy_wizard_state_int_coerces_to_single_wizard_state(legacy_value):
    # The draft (TempData) carries the event type + step, so an in-flight wizard
    # resumes where it left off in the collapsed state.
    assert UserState(legacy_value) is UserState.ADMIN_ADD_EVENT


def test_current_states_still_resolve():
    assert UserState(0) is UserState.DEFAULT
    assert UserState(60) is UserState.ADMIN_ADD_EVENT
    assert UserState(131) is UserState.ADMIN_UPDATE_WEBSITE
    assert UserState(140) is UserState.ADMIN_UPDATE_EVENT_FIELD
    assert UserState(999) is UserState.REJECTED


def test_genuinely_unknown_value_still_raises():
    with pytest.raises(ValueError):
        UserState(9999)


# --- TempData.from_dict: legacy drafts without `step` infer it from filled fields ---

def _legacy_source(**overrides):
    source = {
        'userDocId': 'user-1', 'eventType': Event.GAME, 'timestamp': None,
        'location': None, 'opponent': None, 'chatId': None, 'queryId': None,
    }  # note: no 'step' key — legacy draft
    source.update(overrides)
    return source


def test_legacy_draft_infers_datetime_when_empty():
    assert TempData.from_dict('d1', _legacy_source()).step == EventField.DATETIME


def test_legacy_draft_infers_location_when_timestamp_set():
    src = _legacy_source(timestamp=TS)
    assert TempData.from_dict('d1', src).step == EventField.LOCATION


def test_legacy_game_draft_infers_opponent_when_timestamp_and_location_set():
    src = _legacy_source(timestamp=TS, location='home arena')
    assert TempData.from_dict('d1', src).step == EventField.OPPONENT


def test_legacy_game_draft_infers_save_when_all_fields_set():
    src = _legacy_source(timestamp=TS, location='home arena', opponent='rivals fc')
    assert TempData.from_dict('d1', src).step == EventField.SAVE


def test_legacy_training_draft_infers_save_without_opponent():
    src = _legacy_source(eventType=Event.TRAINING, timestamp=TS, location='sporthalle')
    assert TempData.from_dict('d1', src).step == EventField.SAVE


def test_stored_step_is_used_verbatim_when_present():
    src = _legacy_source(timestamp=TS, step=EventField.DATETIME)
    # Even though timestamp is set (would infer LOCATION), an explicit stored step wins.
    assert TempData.from_dict('d1', src).step == EventField.DATETIME
