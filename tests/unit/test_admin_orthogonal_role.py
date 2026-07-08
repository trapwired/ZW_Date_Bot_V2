"""The point of ADR 0005: admin is a flag, not a role. A non-playing admin runs the
team without appearing anywhere a player would - no reminders, no summaries - while
keeping every admin menu; and legacy ADMIN-role data heals into the new model."""
from Enums.Role import Role
from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from features.events import EventsMenu
from Enums.Event import Event

from tests.helpers import drive, drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 4300
PLAYER_ID = 4301


async def test_retired_admin_is_not_an_active_player(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.RETIRED, UserState.DEFAULT, is_admin=True)
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    # get_all_players feeds every reminder fan-out and attendance overview.
    active = [p.telegramId for p in data_access.get_all_players()]
    assert active == [PLAYER_ID]


async def test_playing_admin_stays_an_active_player(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)

    assert [p.telegramId for p in data_access.get_all_players()] == [ADMIN_ID]


async def test_retired_admin_keeps_the_admin_menu(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.RETIRED, UserState.DEFAULT, is_admin=True)

    await drive(node_handler, ADMIN_ID, 'admin')

    panel = [m for m in bot.sent if m.chat_id == ADMIN_ID][-1]
    assert 'Admin menu' in panel.text
    assert_no_error_reported(bot)


async def test_inactive_admin_keeps_the_admin_menu(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.INACTIVE, UserState.DEFAULT, is_admin=True)

    await drive(node_handler, ADMIN_ID, 'admin')

    panel = [m for m in bot.sent if m.chat_id == ADMIN_ID][-1]
    assert 'Admin menu' in panel.text
    assert_no_error_reported(bot)


async def test_non_admin_player_has_no_admin_menu(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, 'admin')

    sent = [m for m in bot.sent if m.chat_id == PLAYER_ID][-1]
    assert 'Admin menu' not in sent.text
    assert_no_error_reported(bot)


def test_legacy_admin_role_heals_to_player_with_admin_flag():
    healed = UsersToState.from_dict('doc1', {
        'userId': 'u1', 'state': int(UserState.DEFAULT), 'additionalInformation': '',
        'role': 42, 'teamId': 'team1'})

    assert healed.role == Role.PLAYER
    assert healed.is_admin
    assert healed.to_dict()['role'] == Role.PLAYER
    assert healed.to_dict()['isAdmin'] is True


async def test_restarting_retired_admin_is_not_unretired(node_handler, data_access, bot, default_team):
    # /start after a state heal must not silently pull a retired admin back into
    # the active roster (the ADR 0005 persona).
    seed_user(data_access, ADMIN_ID, Role.RETIRED, UserState.INIT, is_admin=True)

    await drive(node_handler, ADMIN_ID, '/start')

    restarted = data_access.get_user_state(ADMIN_ID)
    assert restarted.role == Role.RETIRED and restarted.is_admin
    assert_no_error_reported(bot)


async def test_inactive_admin_can_open_a_timekeeping_card(node_handler, data_access, bot):
    # Admins manage timekeeping events whatever their membership role; the
    # players-only gate must not silently swallow their taps.
    from domain.entities.TimekeepingEvent import TimekeepingEvent
    from domain.EventDateTimeParser import parse
    seed_user(data_access, ADMIN_ID, Role.INACTIVE, UserState.DEFAULT, is_admin=True)
    event = data_access.add(TimekeepingEvent(parse('24.12.2030 18:30').value, 'eventhalle'))

    update = await drive_callback(node_handler, ADMIN_ID,
                                  EventsMenu.encode_card(Event.TIMEKEEPING, event.doc_id))

    assert update.callback_query.edits  # card rendered, not silently dismissed
    assert_no_error_reported(bot)
