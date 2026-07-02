"""DataAccess.get_stats_event summary rules.

- YES shows everyone, including retired/inactive players.
- NO and UNSURE show only active (ADMIN/PLAYER) players.
- A retired/inactive player surfaces only by explicitly saying yes.
- Active players with no attendance record default to UNSURE.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from tests.helpers import seed_user, set_attendance


def test_summary_membership_rules(data_access, game):
    active_no_record = seed_user(data_access, 1, Role.PLAYER, UserState.DEFAULT)
    active_unsure = seed_user(data_access, 2, Role.PLAYER, UserState.DEFAULT)
    active_yes = seed_user(data_access, 3, Role.PLAYER, UserState.DEFAULT)
    active_no = seed_user(data_access, 4, Role.ADMIN, UserState.DEFAULT)
    retired_yes = seed_user(data_access, 5, Role.RETIRED, UserState.DEFAULT)
    retired_unsure = seed_user(data_access, 6, Role.RETIRED, UserState.DEFAULT)
    retired_no = seed_user(data_access, 7, Role.RETIRED, UserState.DEFAULT)
    retired_no_record = seed_user(data_access, 8, Role.RETIRED, UserState.DEFAULT)
    inactive_yes = seed_user(data_access, 9, Role.INACTIVE, UserState.DEFAULT)
    inactive_unsure = seed_user(data_access, 10, Role.INACTIVE, UserState.DEFAULT)

    set_attendance(data_access, active_unsure.user_id, game.doc_id, AttendanceState.UNSURE)
    set_attendance(data_access, active_yes.user_id, game.doc_id, AttendanceState.YES)
    set_attendance(data_access, active_no.user_id, game.doc_id, AttendanceState.NO)
    set_attendance(data_access, retired_yes.user_id, game.doc_id, AttendanceState.YES)
    set_attendance(data_access, retired_unsure.user_id, game.doc_id, AttendanceState.UNSURE)
    set_attendance(data_access, retired_no.user_id, game.doc_id, AttendanceState.NO)
    set_attendance(data_access, inactive_yes.user_id, game.doc_id, AttendanceState.YES)
    set_attendance(data_access, inactive_unsure.user_id, game.doc_id, AttendanceState.UNSURE)

    yes, no, unsure = data_access.get_stats_event(game.doc_id, Event.GAME)
    yes, no, unsure = set(yes), set(no), set(unsure)

    # YES: every yes-sayer, regardless of role
    assert yes == {active_yes.user_id, retired_yes.user_id, inactive_yes.user_id}

    # NO: only active no-sayers (retired_no excluded)
    assert no == {active_no.user_id}

    # UNSURE: active unsure-sayers + active players with no record; never retired/inactive
    assert unsure == {active_unsure.user_id, active_no_record.user_id}

    # Retired/inactive who did not say yes appear nowhere
    everyone_shown = yes | no | unsure
    for hidden in (retired_unsure, retired_no, retired_no_record, inactive_unsure):
        assert hidden.user_id not in everyone_shown
