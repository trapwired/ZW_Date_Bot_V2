"""Characterization: the collapsed admin panel and its two sections.

Frequent actions (events, statistics, roles, announce) stay top-level; rare
configuration nests: 👁 Spectators (password + one-time invites, current values
shown) and ⚙️ Setup (team name, website, trainers).
"""
from Enums.Role import Role
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from Utils import Format
from tests.helpers import drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 2200


def _button_data(edit):
    return [b.callback_data for row in edit.reply_markup.inline_keyboard for b in row]


async def test_panel_is_three_rows_with_the_two_sections(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.PANEL))

    markup = update.callback_query.edits[-1].reply_markup
    assert len(markup.inline_keyboard) == 3 and all(len(row) == 2 for row in markup.inline_keyboard)
    data = _button_data(update.callback_query.edits[-1])
    assert AdminMenu.encode(AdminMenu.SPECTATORS_MENU) in data
    assert AdminMenu.encode(AdminMenu.SETUP_MENU) in data
    assert_no_error_reported(bot)


async def test_spectators_section_shows_password_and_invite_count(node_handler, services, data_access, bot,
                                                                  default_team):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    # Mint through the handler's own TeamService so its cache and the test agree.
    services["team_service"].create_spectator_invite(default_team)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATORS_MENU))

    edit = update.callback_query.edits[-1]
    assert Format.escape(default_team.spectator_password) in edit.text
    assert 'Outstanding invite links: 1' in edit.text
    data = _button_data(edit)
    assert AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_PROMPT) in data
    assert AdminMenu.encode(AdminMenu.SPECTATOR_INVITE) in data
    assert_no_error_reported(bot)


async def test_setup_section_holds_name_website_and_trainers(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SETUP_MENU))

    data = _button_data(update.callback_query.edits[-1])
    assert AdminMenu.encode(AdminMenu.TEAM_NAME_PROMPT) in data
    assert AdminMenu.encode(AdminMenu.WEBSITE_PROMPT) in data
    assert AdminMenu.encode(AdminMenu.TRAINERS_MENU) in data
    assert_no_error_reported(bot)
