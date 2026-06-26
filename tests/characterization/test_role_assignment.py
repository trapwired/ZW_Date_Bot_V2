"""Characterization: the /assign_roles flow (overview entry + list + assign).

Pins AdminNode.handle_assign_roles and AssignRolesCallbackNode before Phase 2b
routes their persistence through RoleService. Role callbacks use the dedicated
ROLES#... channel.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Utils import RoleAssignment
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1200
TARGET_ID = 1201


async def test_assign_roles_entry_shows_overview(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN)

    await drive(node_handler, ADMIN_ID, "/assign_roles")

    assert any("Select a role to manage" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_list_users_by_role_edits_message(node_handler, data_access, bot):
    seed_user(data_access, TARGET_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_list_users(Role.ADMIN))

    assert update.callback_query.edits  # rendered the user list into the message
    assert_no_error_reported(bot)


async def test_assign_role_persists_new_role_and_resets_state(node_handler, data_access, bot):
    target = seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.STATS)

    await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_assign(target.user_id, Role.ADMIN))

    updated = data_access.get_user_state(TARGET_ID)
    assert updated.role == Role.ADMIN
    assert updated.state == UserState.DEFAULT
    assert_no_error_reported(bot)
