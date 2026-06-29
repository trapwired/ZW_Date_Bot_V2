"""Characterization: the website slice.

- Admins update the player-facing URL via a yes/no confirm callback; the pending
  URL is staged in their state's additional_info and committed/discarded through
  WebsiteService.
- The admin menu shows the current URL; players get it as a link button.
"""
from Enums.Role import Role
from Enums.Event import Event
from Enums.UserState import UserState
from Enums.CallbackOption import CallbackOption
from Utils import CallbackUtils
from tests.helpers import drive, drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 1300
PLAYER_ID = 1301

OLD_URL = "https://old.example/club"
NEW_URL = "https://new.example/club"


def _confirm_data(option: CallbackOption) -> str:
    # The website confirm buttons route on ADMIN_UPDATE_WEBSITE (Event.GAME is a filler).
    return CallbackUtils.get_callback_message(UserState.ADMIN_UPDATE_WEBSITE, Event.GAME, option, '')


async def test_confirm_yes_commits_staged_url(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_WEBSITE, additional_info=NEW_URL)

    update = await drive_callback(node_handler, ADMIN_ID, _confirm_data(CallbackOption.YES))

    assert data_access.get_website() == NEW_URL
    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''                 # staging field cleared on commit
    assert staged.state == UserState.ADMIN              # returned to the admin menu
    assert any(NEW_URL in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_confirm_no_keeps_existing_url(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_WEBSITE, additional_info=NEW_URL)

    update = await drive_callback(node_handler, ADMIN_ID, _confirm_data(CallbackOption.NO))

    assert data_access.get_website() == OLD_URL         # unchanged
    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''                 # staging field still cleared
    assert staged.state == UserState.ADMIN
    assert any("Cancelled" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_admin_menu_shows_current_url(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN)

    await drive(node_handler, ADMIN_ID, "/update_website")

    assert any(OLD_URL in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_player_gets_website_link_button(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "/website")

    urls = [m.reply_markup.inline_keyboard[0][0].url
            for m in bot.sent if m.reply_markup is not None]
    assert OLD_URL in urls
    assert_no_error_reported(bot)


async def test_player_website_unconfigured_message(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "/website")

    assert any("not configured" in m.text for m in bot.sent)
    assert_no_error_reported(bot)
