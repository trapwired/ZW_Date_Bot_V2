"""Characterization: the admin spectator-password slice.

Mirrors the website slice (AP#W / AP#WY / AP#WN), but for the per-team spectator
password (AP#K prompts for typed input; AP#KY / AP#KN confirm). The typed password is
staged in the admin's state additional_info and only committed - through
TeamService.set_spectator_password - when they press Save. The password identifies the
team at entry, so it must stay unique across teams.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from domain.entities.Team import Team
from features.adminpanel import AdminMenu
from framework.Services.TeamService import TeamService
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1400
NEW_PASSWORD = "letmewatch"
OTHER_TEAM_GROUP = -100888


def _confirm_button_data(record):
    return [b.callback_data for row in record.reply_markup.inline_keyboard for b in row]


async def test_prompt_moves_to_typed_input_and_shows_current_password(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_PROMPT))

    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD
    assert any(default_team.spectator_password in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_typed_password_restages_menu_message_and_deletes_typed_message(node_handler, data_access, bot,
                                                                             default_team):
    # Entering via the menu tracks that message: the typed password re-renders it with
    # Save/Cancel, the loose typed message is removed, and nothing is persisted yet.
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_PROMPT), message_id=44)

    await drive(node_handler, ADMIN_ID, NEW_PASSWORD)

    from Utils import InlineInputStaging
    menu_edits = [e for e in bot.edits if e.message_id == 44]
    assert any(NEW_PASSWORD in e.text for e in menu_edits)
    confirm_data = _confirm_button_data(menu_edits[-1])
    assert AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_SAVE) in confirm_data
    assert AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_CANCEL) in confirm_data

    _, _, staged = InlineInputStaging.parse(data_access.get_user_state(ADMIN_ID).additional_info)
    assert staged == NEW_PASSWORD
    assert len(bot.deleted) == 1                                       # the loose typed message
    # Fresh read proves nothing was committed to the team document yet.
    assert data_access.get_team(default_team.doc_id).spectator_password == default_team.spectator_password
    assert_no_error_reported(bot)


async def test_save_commits_the_password(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD,
              additional_info=NEW_PASSWORD)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_SAVE))

    # A fresh TeamService reads straight from storage - proves it was persisted, not cached.
    reloaded = TeamService(data_access).get_team(default_team.doc_id)
    assert reloaded.spectator_password == NEW_PASSWORD

    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''
    assert staged.state == UserState.DEFAULT
    # Landing on the spectators overview with the new password IS the confirmation.
    assert any(NEW_PASSWORD in e.text and 'Spectators' in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_save_rejects_password_already_used_by_another_team(node_handler, data_access, bot, default_team):
    data_access.add(Team('Berg', group_chat_id=OTHER_TEAM_GROUP, spectator_password=NEW_PASSWORD))
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD,
              additional_info=NEW_PASSWORD)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_SAVE))

    assert any("Another team already uses" in e.text for e in update.callback_query.edits)
    # The default team's password is untouched...
    assert data_access.get_team(default_team.doc_id).spectator_password == default_team.spectator_password
    # ... and a rejected password keeps the admin in the typed-input state so the next
    # message is simply another attempt.
    assert data_access.get_user_state(ADMIN_ID).state == UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD
    assert_no_error_reported(bot)


async def test_save_rejects_empty_password(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD, additional_info='')

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_SAVE))

    assert any("cannot be used" in e.text for e in update.callback_query.edits)
    assert data_access.get_team(default_team.doc_id).spectator_password == default_team.spectator_password
    assert data_access.get_user_state(ADMIN_ID).state == UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD
    assert_no_error_reported(bot)


async def test_cancel_returns_to_spectators_overview_unchanged(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD,
              additional_info=NEW_PASSWORD)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_PASSWORD_CANCEL))

    assert any("Spectators" in e.text for e in update.callback_query.edits)
    staged = data_access.get_user_state(ADMIN_ID)
    assert staged.additional_info == ''
    assert staged.state == UserState.DEFAULT
    assert data_access.get_team(default_team.doc_id).spectator_password == default_team.spectator_password
    assert_no_error_reported(bot)
