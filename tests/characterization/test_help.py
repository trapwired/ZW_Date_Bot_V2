"""Characterization: help and the static per-role reply keyboard stay consistent.

Both derive from the DEFAULT node's transitions: every keyboard button has a help
entry, admin-only entries are hidden from players, and keyboard-invisible aliases
(/help, /privacy) still work as typed commands.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from framework.CommandDescriptions import CommandDescriptions
from tests.helpers import drive, seed_user, assert_no_error_reported

PLAYER_ID = 1400
ADMIN_ID = 1402
SPECTATOR_ID = 1403


def _keyboard_commands(bot, chat_id):
    record = [m for m in bot.sent if m.chat_id == chat_id][-1]
    return [str(getattr(button, 'text', button)).lower()
            for row in record.reply_markup.keyboard for button in row]


async def test_help_lists_active_commands_with_descriptions(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, 'help')

    help_text = bot.texts_to(PLAYER_ID)[-1]
    for command in ['/help', 'events', 'website', '/privacy']:
        assert f'{command}: {CommandDescriptions.descriptions[command]}' in help_text
    assert 'admin:' not in help_text                    # admin-only, hidden for players
    assert_no_error_reported(bot)


async def test_slash_help_alias_works_but_stays_off_the_keyboard(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, '/help')

    assert 'Here are my available commands' in bot.texts_to(PLAYER_ID)[-1]
    keyboard = _keyboard_commands(bot, PLAYER_ID)
    assert '/help' not in keyboard
    assert '/privacy' not in keyboard
    assert_no_error_reported(bot)


async def test_player_keyboard_is_static_events_website(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, 'help')

    assert _keyboard_commands(bot, PLAYER_ID) == ['events', 'website']
    assert_no_error_reported(bot)


async def test_admin_keyboard_adds_admin_row(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive(node_handler, ADMIN_ID, 'help')

    assert _keyboard_commands(bot, ADMIN_ID) == ['events', 'admin', 'website']
    assert_no_error_reported(bot)


async def test_spectator_keyboard_matches_player_layout(node_handler, data_access, bot):
    seed_user(data_access, SPECTATOR_ID, Role.SPECTATOR, UserState.DEFAULT)

    await drive(node_handler, SPECTATOR_ID, 'help')

    assert _keyboard_commands(bot, SPECTATOR_ID) == ['events', 'website']
    assert_no_error_reported(bot)


async def test_every_keyboard_button_has_a_help_entry(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive(node_handler, ADMIN_ID, 'help')

    help_text = bot.texts_to(ADMIN_ID)[-1]
    for command in _keyboard_commands(bot, ADMIN_ID):
        assert f'{command}: {CommandDescriptions.descriptions[command]}' in help_text
    assert_no_error_reported(bot)


async def test_unknown_text_falls_back_to_help(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, 'foo bar baz')

    assert 'Here are my available commands' in bot.texts_to(PLAYER_ID)[-1]
    assert_no_error_reported(bot)
