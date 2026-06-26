"""Characterization: a player setting attendance + exporting an event to calendar.

Pins EditCallbackNode before Phase 2b-iii routes its persistence through
AttendanceService. Callback-driven (EDIT#<event>#<state>#<doc_id>).
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.AttendanceState import AttendanceState
from databaseEntities.Game import Game
from Utils import CallbackUtils
from domain.EventDateTimeParser import parse
from tests.helpers import drive_callback, seed_user, assert_no_error_reported

PLAYER_ID = 1100
FUTURE = "24.12.2030 18:30"

STATE_OPTIONS = [
    (CallbackOption.YES, AttendanceState.YES),
    (CallbackOption.NO, AttendanceState.NO),
    (CallbackOption.UNSURE, AttendanceState.UNSURE),
]


def _cb(option, doc_id):
    return CallbackUtils.get_callback_message(UserState.EDIT, Event.GAME, option, doc_id)


@pytest.mark.parametrize("option, expected", STATE_OPTIONS)
async def test_set_attendance_persists_chosen_state(node_handler, data_access, bot, option, expected):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    game = data_access.add(Game(parse(FUTURE).value, "home arena", "rivals fc"))

    update = await drive_callback(node_handler, PLAYER_ID, _cb(option, game.doc_id), message_text="old")

    assert data_access.get_attendance(PLAYER_ID, game.doc_id, Event.GAME).state == expected
    assert update.callback_query.answered
    assert_no_error_reported(bot)


async def test_calendar_export_sends_a_document(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    game = data_access.add(Game(parse(FUTURE).value, "home arena", "rivals fc"))

    await drive_callback(node_handler, PLAYER_ID, _cb(CallbackOption.CALENDAR, game.doc_id))

    assert len(bot.documents) == 1
    assert_no_error_reported(bot)
