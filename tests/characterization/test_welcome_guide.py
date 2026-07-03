"""Characterization: the getting-started guide lands right after WELCOME.

Players get it on the /start membership path, spectators after a correct password;
each variant only advertises what that role can actually do (spectators see no
timekeeping/reminders, only admins see the admin panel hint).
"""
from Enums.Role import Role
from Enums.UserState import UserState
from tests.helpers import drive, seed_user, assert_no_error_reported

PLAYER_ID = 1600
SPECTATOR_ID = 1601


async def test_player_gets_guide_after_welcome_on_start(node_handler, data_access, bot, default_team):
    seed_user(data_access, PLAYER_ID, Role.INIT, UserState.INIT, team_id='')

    await drive(node_handler, PLAYER_ID, '/start')

    texts = bot.texts_to(PLAYER_ID)
    assert 'welcome' in texts[0].lower()
    guide = texts[1]
    assert 'events' in guide and 'Reminders' in guide and default_team.name in guide
    assert 'admin' not in guide.lower()
    assert_no_error_reported(bot)


async def test_spectator_gets_read_only_guide_after_password(node_handler, data_access, bot, default_team):
    seed_user(data_access, SPECTATOR_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    await drive(node_handler, SPECTATOR_ID, default_team.spectator_password)

    texts = bot.texts_to(SPECTATOR_ID)
    assert 'welcome' in texts[0].lower()
    guide = texts[1]
    assert 'events' in guide and default_team.name in guide
    assert 'Reminders' not in guide and 'timekeeping' not in guide.lower()
    assert_no_error_reported(bot)
