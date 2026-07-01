"""Characterization: the "event moved by >2h invalidates all attendance" policy.

Pins the domain rule (AttendanceResetPolicy: the `abs(old - new) > 2h` check) applied
by EditEventFieldNode when an event's timestamp is edited.
The flow is text-driven (handle_help -> handle_event_field), so the user is seeded
directly into the single field-edit state (ADMIN_UPDATE_EVENT_FIELD) with the
inline-message context, event type, and DATETIME field stashed in additional_info,
exactly as the callback step would leave it.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.AttendanceState import AttendanceState
from domain.entities.Game import Game
from domain.entities.Attendance import Attendance
from Utils import CallbackUtils
from domain.EventDateTimeParser import parse
from tests.helpers import drive, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 800
ORIGINAL = "24.12.2030 18:30"


def _seed_game_with_yes_attendance(data_access):
    game = data_access.add(Game(parse(ORIGINAL).value, "home arena", "rivals fc"))
    uts = seed_user(
        data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_EVENT_FIELD,
        additional_info=CallbackUtils.build_additional_information(1, ADMIN_ID, game.doc_id, Event.GAME,
                                                                   CallbackOption.DATETIME))
    data_access.update_attendance(Attendance(uts.user_id, game.doc_id, AttendanceState.YES), Event.GAME)
    return game


def _attendance_state(data_access, game):
    return data_access.get_attendance(ADMIN_ID, game.doc_id, Event.GAME).state


async def test_move_more_than_two_hours_resets_attendance_and_notifies(node_handler, data_access, bot):
    game = _seed_game_with_yes_attendance(data_access)
    assert _attendance_state(data_access, game) == AttendanceState.YES

    await drive(node_handler, ADMIN_ID, "24.12.2030 22:00")  # +3.5h

    assert _attendance_state(data_access, game) == AttendanceState.UNSURE
    assert any("more than 2 hours" in m.text for m in bot.sent)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)


async def test_move_less_than_two_hours_keeps_attendance(node_handler, data_access, bot):
    game = _seed_game_with_yes_attendance(data_access)

    await drive(node_handler, ADMIN_ID, "24.12.2030 19:00")  # +0.5h

    assert _attendance_state(data_access, game) == AttendanceState.YES
    assert not any("more than 2 hours" in m.text for m in bot.sent)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)
