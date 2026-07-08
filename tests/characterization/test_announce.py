"""Characterization: the admin announcement slice (AP#N / AP#NP / AP#NG).

Mirrors the other typed-input admin flows: the text is staged in additional_info,
nothing is sent until the admin picks a delivery channel - every player privately
(active roster, spectators excluded) or the team group chat.
"""
from telegram.error import Forbidden

from Enums.Role import Role
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from features.announce.AnnounceService import TELEGRAM_MESSAGE_LIMIT
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1700
PLAYER_ID = 1701
SPECTATOR_ID = 1702
ANNOUNCEMENT = 'Season opener moved to <Saturday>!'


def _seed_team(data_access):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
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


async def test_stale_delivery_button_never_broadcasts_another_flows_staged_value(node_handler, data_access, bot,
                                                                                 default_team):
    # Admin abandoned the announce flow and is now typing a new spectator password;
    # a stale delivery button must not broadcast that staged secret nor kill the flow.
    _seed_team(data_access)
    seed_user(data_access, 1799, Role.PLAYER, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD,
              additional_info='77#1799#SuperSecret99', is_admin=True)

    update = await drive_callback(node_handler, 1799, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_GROUP))

    assert bot.texts_to(default_team.group_chat_id) == []
    assert bot.texts_to(PLAYER_ID) == []
    assert 'no longer active' in update.callback_query.edits[-1].text
    staged = data_access.get_user_state(1799)
    assert staged.state == UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD      # other flow untouched
    assert 'SuperSecret99' in staged.additional_info
    assert_no_error_reported(bot)


async def test_blocked_player_is_not_counted_as_reached(node_handler, data_access, bot):
    _seed_team(data_access)
    original = bot.send_message

    async def send(chat_id, text, reply_markup=None, parse_mode=None):
        if chat_id == PLAYER_ID:
            raise Forbidden('bot was blocked')
        return await original(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    bot.send_message = send
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)
    await drive(node_handler, ADMIN_ID, ANNOUNCEMENT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_PLAYERS))

    assert 'sent to 1 players' in update.callback_query.edits[-1].text


async def test_overlong_announcement_is_rejected_before_staging(node_handler, data_access, bot, default_team):
    _seed_team(data_access)
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)

    await drive(node_handler, ADMIN_ID, 'x' * (TELEGRAM_MESSAGE_LIMIT + 100))
    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_PLAYERS))

    menu_edits = [e for e in bot.edits if e.message_id == 77]
    assert 'too long' in menu_edits[-1].text
    assert 'no announcement text yet' in update.callback_query.edits[-1].text   # nothing was staged
    assert bot.texts_to(PLAYER_ID) == []
    assert_no_error_reported(bot)


async def test_failed_group_post_keeps_flow_alive_and_informs_admin(node_handler, data_access, bot, default_team):
    _seed_team(data_access)
    original = bot.send_message

    async def send(chat_id, text, reply_markup=None, parse_mode=None):
        if chat_id == default_team.group_chat_id:
            raise Forbidden('bot was kicked')
        return await original(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    bot.send_message = send
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_PROMPT), message_id=77)
    await drive(node_handler, ADMIN_ID, ANNOUNCEMENT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.ANNOUNCE_TO_GROUP))

    assert 'Could not post in the group chat' in update.callback_query.edits[-1].text
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ANNOUNCE   # retry stays possible
    assert bot.texts_to(PLAYER_ID) == []
