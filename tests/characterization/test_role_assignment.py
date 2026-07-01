"""Characterization: the /assign_roles flow (overview entry + list + assign) and its
admin-only authorization.

Role callbacks use the dedicated ROLES#... channel and persist through RoleService.
NodeHandler gates callback nodes by the pressing user's role, so the caller is
seeded as an admin for the positive cases.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from features.roles import RoleAssignment
from tests.helpers import drive, drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 1200
TARGET_ID = 1201
NON_ADMIN_ID = 1202


async def test_assign_roles_entry_shows_overview(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN)

    await drive(node_handler, ADMIN_ID, "/assign_roles")

    assert any("Select a role to manage" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_list_users_by_role_edits_message(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN)
    seed_user(data_access, TARGET_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_list_users(Role.ADMIN))

    assert update.callback_query.edits  # rendered the user list into the message
    assert_no_error_reported(bot)


async def test_assign_role_persists_new_role_and_resets_state(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN)
    target = seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.STATS)

    await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_assign(target.user_id, Role.ADMIN))

    updated = data_access.get_user_state(TARGET_ID)
    assert updated.role == Role.ADMIN
    assert updated.state == UserState.DEFAULT
    assert_no_error_reported(bot)


async def test_non_admin_cannot_assign_roles(node_handler, data_access, bot):
    seed_user(data_access, NON_ADMIN_ID, Role.PLAYER, UserState.DEFAULT)
    target = seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.DEFAULT)

    # A non-admin pressing a forwarded ASSIGN button must not change anyone's role.
    await drive_callback(node_handler, NON_ADMIN_ID, RoleAssignment.encode_assign(target.user_id, Role.ADMIN))

    assert data_access.get_user_state(TARGET_ID).role == Role.PLAYER
    assert_no_error_reported(bot)
