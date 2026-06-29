"""Characterization: the stats slice.

Admin reminder/event statistics screens and the reset-statistics confirm callback
now read/write through StatisticsService instead of DataAccess directly.
"""
from Enums.Role import Role
from Enums.Event import Event
from Enums.UserState import UserState
from Enums.CallbackOption import CallbackOption
from Utils import CallbackUtils
from tests.helpers import drive, drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 1400


def _reset_data(option: CallbackOption) -> str:
    # The reset-statistics confirm buttons route on ADMIN_STATISTICS (the screen the admin is on).
    return CallbackUtils.get_callback_message(UserState.ADMIN_STATISTICS, Event.GAME, option, '')


async def test_reset_statistics_yes_confirms(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_STATISTICS)

    update = await drive_callback(node_handler, ADMIN_ID, _reset_data(CallbackOption.YES))

    assert any("season has ended" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_reset_statistics_no_cancels(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_STATISTICS)

    update = await drive_callback(node_handler, ADMIN_ID, _reset_data(CallbackOption.NO))

    assert any("Cancelled" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_admin_reminder_statistics_renders(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_STATISTICS)

    await drive(node_handler, ADMIN_ID, "/reminder_statistics")

    assert bot.sent  # a statistics message went out without error
    assert_no_error_reported(bot)


async def test_admin_event_statistics_renders(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_STATISTICS)

    await drive(node_handler, ADMIN_ID, "/game_statistics")

    assert bot.sent
    assert_no_error_reported(bot)
