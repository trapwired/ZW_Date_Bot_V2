"""Characterization: team stamp on admin callback data.

Admin menus (AP#, ROLES#) rendered for one team must not act when pressed by an
admin of another team (forwarded messages keep working buttons). The rendering
team's id is stamped into the callback data; NodeHandler drops mismatches.
Pre-stamp buttons carry no stamp and keep working.
"""
from Enums.Event import Event
from Enums.Role import Role
from Enums.UserState import UserState
from domain.entities.Team import Team
from features.adminpanel import AdminMenu
from features.roles import RoleAssignment
from framework import TeamStamp
from framework.Services.TeamService import TeamService
from tests.helpers import drive_callback, seed_user, assert_no_error_reported

FOREIGN_ADMIN_ID = 2000
TEAM_B_GROUP = -200888111


def _foreign_admin(data_access):
    team_b = data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP))
    return seed_user(data_access, FOREIGN_ADMIN_ID, Role.PLAYER, UserState.DEFAULT, team_id=team_b.doc_id, is_admin=True)


async def test_foreign_admin_pressing_forwarded_trainer_toggle_writes_nothing(node_handler, data_access, bot,
                                                                              default_team):
    _foreign_admin(data_access)
    # Rendered inside the default team's context -> stamped with the default team's id.
    foreign_button = AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME), FOREIGN_ADMIN_ID)

    update = await drive_callback(node_handler, FOREIGN_ADMIN_ID, foreign_button)

    for team in TeamService(data_access).get_all_teams():
        assert FOREIGN_ADMIN_ID not in team.trainers_games
    assert 'different team' in update.callback_query.edits[-1].text
    assert_no_error_reported(bot)


async def test_foreign_admin_pressing_forwarded_role_button_changes_nothing(node_handler, data_access, bot):
    _foreign_admin(data_access)
    victim = seed_user(data_access, FOREIGN_ADMIN_ID + 1, Role.PLAYER, UserState.DEFAULT)
    foreign_button = RoleAssignment.encode_assign(victim.user_id, Role.INACTIVE)

    update = await drive_callback(node_handler, FOREIGN_ADMIN_ID, foreign_button)

    assert data_access.get_user_state(FOREIGN_ADMIN_ID + 1).role == Role.PLAYER
    assert 'different team' in update.callback_query.edits[-1].text
    assert_no_error_reported(bot)


async def test_pre_stamp_buttons_keep_working(node_handler, data_access, bot):
    seed_user(data_access, FOREIGN_ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    legacy_button = TeamStamp.strip(AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME),
                                                     FOREIGN_ADMIN_ID))

    await drive_callback(node_handler, FOREIGN_ADMIN_ID, legacy_button)

    team = TeamService(data_access).get_all_teams()[0]
    assert FOREIGN_ADMIN_ID in team.trainers_games
    assert_no_error_reported(bot)


def test_longest_stamped_callback_fits_telegrams_64_byte_limit():
    from data.TenantContext import team_context
    doc_id = 'x' * 20                                     # Firestore auto-id length
    with team_context(doc_id):
        bare = TeamStamp.strip(RoleAssignment.encode_assign(doc_id, Role.INACTIVE))
    padded = f'{bare}{TeamStamp.DELIMITER}{TeamStamp.MARKER}{doc_id}'   # worst-case stamp length
    assert len(padded.encode()) <= 64
