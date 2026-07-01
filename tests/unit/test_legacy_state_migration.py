"""Unit: backward-compat for Phase 3a's add-wizard state collapse.

A user mid-wizard (or a draft in flight) at deploy time carries pre-3a persisted
values. Reading them back must not crash and must not lose progress.
"""
import pandas as pd
import pytest

from Enums.CallbackOption import CallbackOption
from Enums.Event import Event
from Enums.UserState import UserState
from databaseEntities.TempData import TempData

# Persisted timestamps come back as tz-aware pd.Timestamp objects, not strings.
TS = pd.Timestamp("2030-12-24 18:30", tz="UTC")


# --- UserState._missing_: legacy add-field ints coerce to the parent state ---

@pytest.mark.parametrize("legacy_value, expected", [
    (103, UserState.ADMIN_ADD_GAME),        # ADMIN_ADD_GAME_TIMESTAMP
    (104, UserState.ADMIN_ADD_GAME),        # ADMIN_ADD_GAME_LOCATION
    (105, UserState.ADMIN_ADD_GAME),        # ADMIN_ADD_GAME_OPPONENT
    (106, UserState.ADMIN_ADD_GAME),        # ADMIN_FINISH_ADD_GAME
    (114, UserState.ADMIN_ADD_TRAINING),    # ADMIN_ADD_TRAINING_TIMESTAMP
    (115, UserState.ADMIN_ADD_TRAINING),    # ADMIN_FINISH_ADD_TRAINING
    (124, UserState.ADMIN_ADD_TIMEKEEPING),  # ADMIN_ADD_TIMEKEEPING_TIMESTAMP
    (125, UserState.ADMIN_ADD_TIMEKEEPING),  # ADMIN_FINISH_ADD_TIMEKEEPING
])
def test_legacy_add_state_int_coerces_to_parent(legacy_value, expected):
    assert UserState(legacy_value) is expected


def test_current_states_still_resolve():
    assert UserState(56) is UserState.ADMIN_ADD_GAME
    assert UserState(999) is UserState.REJECTED


def test_genuinely_unknown_value_still_raises():
    with pytest.raises(ValueError):
        UserState(9999)


# --- TempData.from_dict: legacy drafts without `step` infer it from filled fields ---

def _legacy_source(**overrides):
    source = {
        'userDocId': 'user-1', 'eventType': Event.GAME, 'timestamp': None,
        'location': None, 'opponent': None, 'chatId': None, 'queryId': None,
    }  # note: no 'step' key — pre-3a draft
    source.update(overrides)
    return source


def test_legacy_draft_infers_datetime_when_empty():
    assert TempData.from_dict('d1', _legacy_source()).step == CallbackOption.DATETIME


def test_legacy_draft_infers_location_when_timestamp_set():
    src = _legacy_source(timestamp=TS)
    assert TempData.from_dict('d1', src).step == CallbackOption.LOCATION


def test_legacy_game_draft_infers_opponent_when_timestamp_and_location_set():
    src = _legacy_source(timestamp=TS, location='home arena')
    assert TempData.from_dict('d1', src).step == CallbackOption.OPPONENT


def test_legacy_game_draft_infers_save_when_all_fields_set():
    src = _legacy_source(timestamp=TS, location='home arena', opponent='rivals fc')
    assert TempData.from_dict('d1', src).step == CallbackOption.SAVE


def test_legacy_training_draft_infers_save_without_opponent():
    src = _legacy_source(eventType=Event.TRAINING, timestamp=TS, location='sporthalle')
    assert TempData.from_dict('d1', src).step == CallbackOption.SAVE


def test_stored_step_is_used_verbatim_when_present():
    src = _legacy_source(timestamp=TS, step=CallbackOption.DATETIME)
    # Even though timestamp is set (would infer LOCATION), an explicit stored step wins.
    assert TempData.from_dict('d1', src).step == CallbackOption.DATETIME
