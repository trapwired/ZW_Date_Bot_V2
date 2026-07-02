"""Characterization: the admin menu's statistics screens and season reset.

All inline (AP#S / AP#RC / AP#RY): the one menu message is edited in place; the reset
asks for confirmation first. Non-admins pressing forwarded buttons are blocked by the
NodeHandler role gate.
"""
from Enums.Role import Role
from Enums.Event import Event
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from tests.helpers import drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 1400
PLAYER_ID = 1401


async def test_statistics_menu_lists_all_statistic_screens(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.STATS_MENU))

    edit = update.callback_query.edits[-1]
    data = [b.callback_data for row in edit.reply_markup.inline_keyboard for b in row]
    assert AdminMenu.encode(AdminMenu.STATS_MENU, AdminMenu.REMINDER_STATISTICS) in data
    assert AdminMenu.encode(AdminMenu.STATS_MENU, int(Event.GAME)) in data
    assert AdminMenu.encode(AdminMenu.RESET_CONFIRM) in data
    assert_no_error_reported(bot)


async def test_reminder_statistics_render_into_the_menu_message(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID,
                                  AdminMenu.encode(AdminMenu.STATS_MENU, AdminMenu.REMINDER_STATISTICS))

    assert any("Statistics" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_event_statistics_render_into_the_menu_message(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID,
                                  AdminMenu.encode(AdminMenu.STATS_MENU, int(Event.GAME)))

    assert any("Game" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_reset_statistics_asks_for_confirmation_then_resets(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.RESET_CONFIRM))
    assert any("Are you sure" in e.text for e in update.callback_query.edits)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.RESET_CONFIRMED))
    assert any("season has ended" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_non_admin_cannot_reach_admin_menu_actions(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, AdminMenu.encode(AdminMenu.RESET_CONFIRMED))

    assert update.callback_query.answered
    assert not update.callback_query.edits
    assert_no_error_reported(bot)
