"""Characterization: a player setting attendance + exporting an event to calendar.

Attendance presses (EV#A) persist via AttendanceService and re-render the card in
place. Pre-redesign attendance buttons (EDIT#...) on already-delivered messages must
keep working through the legacy adapter.
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from features.events import EventsMenu
from tests.helpers import drive_callback, seed_user, assert_no_error_reported

PLAYER_ID = 1100
SPECTATOR_ID = 1101


@pytest.mark.parametrize("state", [AttendanceState.YES, AttendanceState.NO, AttendanceState.UNSURE])
async def test_set_attendance_persists_chosen_state(node_handler, data_access, bot, game, state):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID,
                                  EventsMenu.encode_attend(Event.GAME, game.doc_id, state))

    assert data_access.get_attendance(PLAYER_ID, game.doc_id, Event.GAME).state == state
    assert update.callback_query.answered
    assert update.callback_query.edits            # card re-rendered in place
    assert_no_error_reported(bot)


async def test_legacy_attendance_button_still_works(node_handler, data_access, bot, game):
    # Exact wire format of buttons on messages sent before the menu redesign.
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive_callback(node_handler, PLAYER_ID, f"EDIT#GAME#YES#{game.doc_id}")

    assert data_access.get_attendance(PLAYER_ID, game.doc_id, Event.GAME).state == AttendanceState.YES
    assert_no_error_reported(bot)


async def test_spectator_cannot_set_attendance(node_handler, data_access, bot, game):
    # e.g. a forwarded attendance button: the press is dismissed without a write.
    seed_user(data_access, SPECTATOR_ID, Role.SPECTATOR, UserState.DEFAULT)

    update = await drive_callback(node_handler, SPECTATOR_ID,
                                  EventsMenu.encode_attend(Event.GAME, game.doc_id, AttendanceState.YES))

    assert data_access.get_attendance(SPECTATOR_ID, game.doc_id, Event.GAME).state == AttendanceState.UNSURE
    assert update.callback_query.answered
    assert not update.callback_query.edits
    assert_no_error_reported(bot)


async def test_calendar_export_sends_a_document(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_calendar(Event.GAME, game.doc_id))

    assert len(bot.documents) == 1
    assert_no_error_reported(bot)


async def test_legacy_calendar_button_still_works(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive_callback(node_handler, PLAYER_ID, f"EDIT#GAME#CALENDAR#{game.doc_id}")

    assert len(bot.documents) == 1
    assert_no_error_reported(bot)


async def test_expired_pre_redesign_menu_button_degrades_gracefully(node_handler, data_access, bot, game):
    # Buttons from retired flows (e.g. the old update/delete menu) are answered with an
    # expired-menu notice instead of alerting the maintainer.
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, f"ADMIN_UPDATE#GAME#UPDATE#{game.doc_id}")

    assert update.callback_query.answered
    assert any("no longer works" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)
