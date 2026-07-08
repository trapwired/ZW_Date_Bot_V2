"""Characterization: the role-assignment flow (overview entry + list + assign) and its
admin-only authorization.

Role callbacks use the dedicated ROLES#... channel and persist through RoleService.
The entry point is the admin menu's Roles button (ROLES#H). NodeHandler gates callback
nodes by the pressing user's admin flag, so the caller is seeded as an admin for the
positive cases.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from features.roles import RoleAssignment
from tests.helpers import drive, drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 1200
TARGET_ID = 1201
NON_ADMIN_ID = 1202


async def test_admin_menu_offers_the_roles_entry(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)

    await drive(node_handler, ADMIN_ID, "admin")

    panel = [m for m in bot.sent if m.chat_id == ADMIN_ID][-1]
    data = [b.callback_data for row in panel.reply_markup.inline_keyboard for b in row]
    assert RoleAssignment.encode_home() in data
    assert_no_error_reported(bot)


async def test_roles_entry_shows_overview_with_back_to_admin_menu(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_home())

    edit = update.callback_query.edits[-1]
    assert "Select a role to manage" in edit.text
    data = [b.callback_data for row in edit.reply_markup.inline_keyboard for b in row]
    from features.adminpanel import AdminMenu
    assert AdminMenu.encode(AdminMenu.PANEL) in data    # « Back into the admin menu
    assert_no_error_reported(bot)


async def test_list_users_by_role_edits_message(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_list_users(Role.PLAYER))

    assert update.callback_query.edits  # rendered the user list into the message
    assert_no_error_reported(bot)


async def test_admin_list_shows_admins_of_any_role(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    seed_user(data_access, TARGET_ID, Role.RETIRED, UserState.DEFAULT, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_list_admins())

    edit = update.callback_query.edits[-1]
    assert 'Current admins' in edit.text
    labels = [b.text for row in edit.reply_markup.inline_keyboard for b in row]
    assert any('RETIRED' in label and RoleAssignment.ADMIN_MARKER in label for label in labels)
    assert_no_error_reported(bot)


async def test_assign_role_persists_new_role_and_resets_state(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    target = seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE)

    await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_assign(target.user_id, Role.RETIRED))

    updated = data_access.get_user_state(TARGET_ID)
    assert updated.role == Role.RETIRED
    assert updated.state == UserState.DEFAULT
    assert_no_error_reported(bot)


async def test_toggle_admin_flips_flag_and_keeps_role(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    target = seed_user(data_access, TARGET_ID, Role.RETIRED, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID, RoleAssignment.encode_toggle_admin(target.user_id))

    updated = data_access.get_user_state(TARGET_ID)
    assert updated.is_admin and updated.role == Role.RETIRED
    assert_no_error_reported(bot)


async def test_legacy_assign_admin_button_grants_the_flag(node_handler, data_access, bot):
    # Buttons minted before the refactor encode the retired ADMIN role value 42.
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    target = seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.DEFAULT)

    legacy_assign = RoleAssignment._encode(RoleAssignment.ASSIGN, target.user_id, 42)
    await drive_callback(node_handler, ADMIN_ID, legacy_assign)

    updated = data_access.get_user_state(TARGET_ID)
    assert updated.is_admin and updated.role == Role.PLAYER
    assert_no_error_reported(bot)


async def test_non_admin_cannot_assign_roles(node_handler, data_access, bot):
    seed_user(data_access, NON_ADMIN_ID, Role.PLAYER, UserState.DEFAULT)
    target = seed_user(data_access, TARGET_ID, Role.PLAYER, UserState.DEFAULT)

    # A non-admin pressing a forwarded ASSIGN button must not change anyone's role.
    await drive_callback(node_handler, NON_ADMIN_ID, RoleAssignment.encode_assign(target.user_id, Role.RETIRED))

    assert data_access.get_user_state(TARGET_ID).role == Role.PLAYER
    assert_no_error_reported(bot)
