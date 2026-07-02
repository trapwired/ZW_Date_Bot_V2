"""Characterization: /help stays consistent with the keyboard.

Help and the reply keyboard derive from the same active-transition selection
(Node.get_active_transitions): an option hidden from the keyboard (inactive
is_active_function, e.g. no upcoming games) must not be explained in help,
and every described keyboard option gets its explanation.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from framework.CommandDescriptions import CommandDescriptions
from domain.entities.Game import Game
from domain.EventDateTimeParser import parse
from tests.helpers import drive, seed_user, assert_no_error_reported

PLAYER_ID = 1400

FUTURE = "24.12.2030 18:30"


def _keyboard_commands(bot, chat_id):
    record = [m for m in bot.sent if m.chat_id == chat_id][-1]
    return [str(getattr(button, 'text', button)).lower()
            for row in record.reply_markup.keyboard for button in row]


async def test_help_lists_active_commands_with_descriptions(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, '/help')

    help_text = bot.texts_to(PLAYER_ID)[-1]
    for command in ['/help', '/website', '/stats', '/edit']:
        assert f'{command}: {CommandDescriptions.descriptions[command]}' in help_text
    assert '/admin' not in help_text                    # admin-only, hidden for players
    assert_no_error_reported(bot)


async def test_help_matches_keyboard(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, '/help')

    help_text = bot.texts_to(PLAYER_ID)[-1]
    for command in _keyboard_commands(bot, PLAYER_ID):
        assert f'{command}: {CommandDescriptions.descriptions[command]}' in help_text
    assert_no_error_reported(bot)


async def test_help_hides_inactive_commands(node_handler, data_access, bot):
    # No upcoming games/trainings/timekeepings: /games etc. are inactive, so the
    # keyboard hides them — help must not explain them either.
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.STATS)

    await drive(node_handler, PLAYER_ID, '/help')

    help_text = bot.texts_to(PLAYER_ID)[-1]
    assert '/games' not in help_text
    assert '/games' not in _keyboard_commands(bot, PLAYER_ID)
    assert 'continue later' in help_text
    assert_no_error_reported(bot)


async def test_help_shows_command_once_event_exists(node_handler, data_access, bot):
    data_access.add(Game(parse(FUTURE).value, "home arena", "rivals fc"))
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.STATS)

    await drive(node_handler, PLAYER_ID, '/help')

    help_text = bot.texts_to(PLAYER_ID)[-1]
    assert f'/games: {CommandDescriptions.descriptions["/games"]}' in help_text
    assert '/games' in _keyboard_commands(bot, PLAYER_ID)
    assert_no_error_reported(bot)
