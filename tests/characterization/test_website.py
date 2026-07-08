"""Characterization: the website slice.

- Admins update the player-facing URL from the admin menu (AP#W prompts for typed
  input; AP#WY / AP#WN confirm); the pending URL is staged in their state's
  additional_info and committed/discarded through WebsiteService.
- Players get the URL as a link button via the 'website' keyboard entry.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1300
PLAYER_ID = 1301

OLD_URL = "https://old.example/club"
NEW_URL = "https://new.example/club"


async def test_set_website_prompts_and_moves_to_typed_input(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_PROMPT))

    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_UPDATE_WEBSITE
    assert any(OLD_URL in e.text for e in update.callback_query.edits)  # shows the current URL
    assert_no_error_reported(bot)


async def test_typed_url_is_staged_and_confirmation_asked(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE, is_admin=True)

    await drive(node_handler, ADMIN_ID, NEW_URL)

    from Utils import InlineInputStaging
    assert data_access.get_website() is None                       # nothing committed yet
    _, _, staged_url = InlineInputStaging.parse(data_access.get_user_state(ADMIN_ID).additional_info)
    assert staged_url == NEW_URL
    confirm = [m for m in bot.sent if m.chat_id == ADMIN_ID][-1]
    data = [b.callback_data for row in confirm.reply_markup.inline_keyboard for b in row]
    assert AdminMenu.encode(AdminMenu.WEBSITE_YES) in data
    assert AdminMenu.encode(AdminMenu.WEBSITE_NO) in data
    assert_no_error_reported(bot)


async def test_typed_url_updates_the_menu_message_in_place(node_handler, data_access, bot):
    # Entering via the admin menu tracks that message: every typed URL re-renders it
    # with Save/Cancel and the loose typed message is removed from the chat.
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_PROMPT), message_id=33)

    await drive(node_handler, ADMIN_ID, NEW_URL)
    await drive(node_handler, ADMIN_ID, OLD_URL)     # retyping replaces the staged value

    from Utils import InlineInputStaging
    menu_edits = [e for e in bot.edits if e.message_id == 33]
    assert any(NEW_URL in e.text for e in menu_edits)
    assert any(OLD_URL in e.text for e in menu_edits)          # second URL re-rendered in place
    _, _, staged_url = InlineInputStaging.parse(data_access.get_user_state(ADMIN_ID).additional_info)
    assert staged_url == OLD_URL
    assert data_access.get_website() is None                   # still nothing committed
    assert len(bot.deleted) == 2                               # both typed URL messages cleaned up
    assert_no_error_reported(bot)


async def test_confirm_yes_commits_staged_url(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE, additional_info=NEW_URL, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_YES))

    assert data_access.get_website() == NEW_URL
    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''                 # staging field cleared on commit
    assert staged.state == UserState.DEFAULT            # back on the main menu
    assert any(NEW_URL in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_confirm_no_keeps_existing_url(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE, additional_info=NEW_URL, is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_NO))

    assert data_access.get_website() == OLD_URL         # unchanged
    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''                 # staging field still cleared
    assert staged.state == UserState.DEFAULT
    assert any("Team setup" in e.text for e in update.callback_query.edits)  # back on the setup overview
    assert_no_error_reported(bot)


async def test_confirm_yes_normalizes_schemeless_host(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE, additional_info="www.google.com", is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_YES))

    assert data_access.get_website() == "https://www.google.com"   # scheme defaulted to https
    assert data_access.get_user_state(ADMIN_ID).additional_info == ''
    assert any("https://www.google.com" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_confirm_yes_rejects_invalid_url(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE, additional_info="not a url", is_admin=True)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_YES))

    assert data_access.get_website() == OLD_URL         # invalid input not stored
    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''                 # staging field still cleared
    assert any("valid URL" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_confirm_yes_rejects_whitespace_url(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.ADMIN_UPDATE_WEBSITE, additional_info="   ", is_admin=True)

    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WEBSITE_YES))

    assert data_access.get_website() is None            # nothing committed
    assert data_access.get_user_state(ADMIN_ID).additional_info == ''
    assert_no_error_reported(bot)


async def test_player_gets_website_link_button(node_handler, data_access, bot):
    data_access.set_website(OLD_URL)
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "Website")

    urls = [m.reply_markup.inline_keyboard[0][0].url
            for m in bot.sent if m.reply_markup is not None]
    assert OLD_URL in urls
    assert_no_error_reported(bot)


async def test_player_website_unconfigured_message(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "website")

    assert any("not configured" in m.text for m in bot.sent)
    assert_no_error_reported(bot)
