"""Characterization: the admin announcement slice (AP#N / AP#NP / AP#NG).

Mirrors the other typed-input admin flows: the text is staged in additional_info,
nothing is sent until the admin picks a delivery channel - every player privately
(active roster, spectators excluded) or the team group chat.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1700
PLAYER_ID = 1701
SPECTATOR_ID = 1702
ANNOUNCEMENT = 'Season opener moved to <Saturday>!'


def _seed_team(data_access):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    seed_user(data_access, SPECTATOR_ID, Role.SPECTATOR, UserState.DEFAULT)


async def test_prompt_moves_to_typed_input(node_handler, data_access, bot):
    _seed_team(data_access)

    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT))

    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ANNOUNCE
    assert_no_error_reported(bot)


async def test_typed_text_shows_delivery_choice_and_sends_nothing(node_handler, data_access, bot, default_team):
    _seed_team(data_access)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)

    await drive(node_handler, ADMIN_ID, ANNOUNCEMENT)

    menu_edits = [e for e in bot.edits if e.message_id == 77]
    button_data = [b.callback_data for row in menu_edits[-1].reply_markup.inline_keyboard for b in row]
    assert AdminMenu.encode(AdminMenu.ANNOUNCE_TO_PLAYERS) in button_data
    assert AdminMenu.encode(AdminMenu.ANNOUNCE_TO_GROUP) in button_data
    assert bot.texts_to(PLAYER_ID) == []
    assert bot.texts_to(default_team.group_chat_id) == []
    assert_no_error_reported(bot)


async def test_send_to_players_reaches_active_roster_only(node_handler, data_access, bot, default_team):
    _seed_team(data_access)
    seed_user(data_access, ADMIN_ID + 100, Role.RETIRED, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)
    await drive(node_handler, ADMIN_ID, ANNOUNCEMENT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_PLAYERS))

    for recipient in (ADMIN_ID, PLAYER_ID):
        texts = bot.texts_to(recipient)
        assert len(texts) == 1 and 'Announcement' in texts[0]
        assert '&lt;Saturday&gt;' in texts[0]                      # typed text lands HTML-escaped
    assert bot.texts_to(SPECTATOR_ID) == []
    assert bot.texts_to(ADMIN_ID + 100) == []
    assert bot.texts_to(default_team.group_chat_id) == []
    assert 'sent to 2 players' in update.callback_query.edits[-1].text
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert data_access.get_user_state(ADMIN_ID).additional_info == ''
    assert_no_error_reported(bot)


async def test_send_to_group_posts_once_and_dms_nobody(node_handler, data_access, bot, default_team):
    _seed_team(data_access)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)
    await drive(node_handler, ADMIN_ID, ANNOUNCEMENT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_GROUP))

    group_texts = bot.texts_to(default_team.group_chat_id)
    assert len(group_texts) == 1 and 'Announcement' in group_texts[0]
    assert bot.texts_to(PLAYER_ID) == []
    assert 'posted in the group chat' in update.callback_query.edits[-1].text
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert_no_error_reported(bot)


async def test_delivery_without_text_keeps_prompting(node_handler, data_access, bot, default_team):
    _seed_team(data_access)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_PLAYERS))

    assert 'no announcement text yet' in update.callback_query.edits[-1].text
    assert bot.texts_to(PLAYER_ID) == []
    assert bot.texts_to(default_team.group_chat_id) == []
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ANNOUNCE
    assert_no_error_reported(bot)
