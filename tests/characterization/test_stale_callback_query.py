"""Characterization: a callback query that expired before the bot could answer it.

Happens whenever a button press sits in the update queue past Telegram's callback
timeout - i.e. the bot was offline or restarting (deploys). answer() then raises
BadRequest('Query is too old...') mid-handler. The presser must get an explanation
instead of a dead button, and the maintainer must NOT get an error report.
"""
from telegram.error import BadRequest

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role
from Enums.UserState import UserState
from features.events import EventsMenu
from tests.helpers import drive_callback, make_callback_update, seed_user, assert_no_error_reported

STALE_QUERY_ERROR = BadRequest('Query is too old and response timeout expired or query id is invalid')
PLAYER_ID = 4242


async def _drive_stale_callback(node_handler, chat_id: int, data: str):
    update = make_callback_update(chat_id, data)

    async def stale_answer(*args, **kwargs):
        raise STALE_QUERY_ERROR

    update.callback_query.answer = stale_answer
    await node_handler.handle_message(update, context=None)
    return update


async def test_stale_attendance_press_informs_presser_not_maintainer(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    button = EventsMenu.encode_attend(Event.GAME, game.doc_id, AttendanceState.YES)

    await _drive_stale_callback(node_handler, PLAYER_ID, button)

    assert_no_error_reported(bot)
    presser_messages = [m.text for m in bot.sent if m.chat_id == PLAYER_ID]
    assert any('too late' in m for m in presser_messages), presser_messages


async def test_stale_press_still_records_the_attendance(node_handler, data_access, bot, game):
    # The write happens before answer() raises - the tap counts even though the
    # card refresh is lost. The explanation message tells the presser to re-check.
    user_to_state = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    button = EventsMenu.encode_attend(Event.GAME, game.doc_id, AttendanceState.YES)

    await _drive_stale_callback(node_handler, PLAYER_ID, button)

    attendance = data_access.get_attendance(PLAYER_ID, game.doc_id, Event.GAME)
    assert attendance.state == AttendanceState.YES


async def test_fresh_callback_still_works_unchanged(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    button = EventsMenu.encode_attend(Event.GAME, game.doc_id, AttendanceState.YES)

    update = await drive_callback(node_handler, PLAYER_ID, button)

    assert update.callback_query.answered
    assert_no_error_reported(bot)
    assert not any('too late' in m.text for m in bot.sent)
