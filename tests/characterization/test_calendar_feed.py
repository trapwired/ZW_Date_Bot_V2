"""Characterization: the calendar subscription in the bot (plan §7, §10).

The 📆 row in the events list and /calendar both answer in the private chat: the first
time with a fresh link plus subscribe steps, later with the link's status and a 🔄
button that replaces the link. The feed itself is reached over HTTP; here we only
check that the link the bot hands out is the one that renders."""
import logging
import re

import pytest

from Enums.Role import Role
from Enums.UserState import UserState

from features.calendarfeed.CalendarFeedService import CalendarFeedConfig, CalendarFeedService

from tests.helpers import drive, drive_callback, drive_group, seed_user, assert_no_error_reported, forbid_chat

PLAYER_ID = 7300
SPECTATOR_ID = 7301
INACTIVE_ID = 7302
GROUP_CHAT_ID = -100730

LINK = re.compile(r'<code>(http://test\.local/cal/([A-Za-z0-9_-]{40}\.ics))</code>')


def _buttons(message):
    return [button for row in message.reply_markup.inline_keyboard for button in row]


def _last_message(bot, chat_id):
    return [m for m in bot.sent if m.chat_id == chat_id][-1]


def _maintainer_texts(bot) -> list[str]:
    return [m.text for m in bot.sent if m.chat_id not in (PLAYER_ID, SPECTATOR_ID, INACTIVE_ID)]


def _issued_file_name(message) -> str:
    match = LINK.search(message.text)
    assert match, f'no tap-to-copy link in: {message.text!r}'
    return match.group(2)


@pytest.fixture
def calendar_feed_service(services):
    return services['calendar_feed_service']


@pytest.fixture
def node_handler_feature_off(bot, api_config, data_access, services):
    from framework.NodeHandler import NodeHandler
    return NodeHandler(
        bot, api_config,
        services["telegram_service"], services["user_state_service"],
        services["ics_service"], data_access, services["trigger_service"], services["event_service"],
        services["attendance_service"], services["role_service"], services["website_service"],
        services["statistics_service"], services["team_service"],
        CalendarFeedService(data_access, CalendarFeedConfig('', 8080)),
    )


# --- the entry row -----------------------------------------------------------------------

@pytest.mark.parametrize('telegram_id, role', [(PLAYER_ID, Role.PLAYER), (SPECTATOR_ID, Role.SPECTATOR)])
async def test_events_list_offers_the_subscription(node_handler, data_access, bot, game, telegram_id, role):
    seed_user(data_access, telegram_id, role, UserState.DEFAULT)

    await drive(node_handler, telegram_id, 'events')

    data = [b.callback_data for b in _buttons(_last_message(bot, telegram_id))]
    assert data[-2:] == ['CAL#S', 'LANG#P']  # right before the language row
    assert_no_error_reported(bot)


async def test_empty_events_list_still_offers_the_subscription(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, 'events')

    assert [b.callback_data for b in _buttons(_last_message(bot, PLAYER_ID))] == ['CAL#S', 'LANG#P']


async def test_no_row_while_the_feature_is_off(node_handler_feature_off, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler_feature_off, PLAYER_ID, 'events')

    data = [b.callback_data for b in _buttons(_last_message(bot, PLAYER_ID))]
    assert 'CAL#S' not in data
    assert_no_error_reported(bot)


# --- tapping the row ---------------------------------------------------------------------

async def test_first_tap_sends_a_fresh_link_with_steps(node_handler, data_access, bot, calendar_feed_service, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, 'CAL#S')

    assert update.callback_query.answered
    message = _last_message(bot, PLAYER_ID)
    assert message.parse_mode == 'HTML'
    assert 'iPhone' in message.text and 'Android' in message.text
    google, rotate = _buttons(message)
    assert google.url.startswith('https://www.google.com/calendar/render?cid=webcal%3A%2F%2Ftest.local%2Fcal%2F')
    assert rotate.callback_data == 'CAL#R'
    # The link the bot hands out is the one that renders.
    assert calendar_feed_service.render_feed(_issued_file_name(message)).startswith('BEGIN:VCALENDAR')
    assert_no_error_reported(bot)


async def test_later_tap_shows_status_instead_of_a_new_link(node_handler, data_access, bot, calendar_feed_service):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    await drive_callback(node_handler, PLAYER_ID, 'CAL#S')
    first_file_name = _issued_file_name(_last_message(bot, PLAYER_ID))

    await drive_callback(node_handler, PLAYER_ID, 'CAL#S')

    status = _last_message(bot, PLAYER_ID)
    assert 'You already have a calendar link' in status.text
    assert 'last fetched: never' in status.text
    assert not LINK.search(status.text)
    assert [b.callback_data for b in _buttons(status)] == ['CAL#R']
    # Looking at the status changes nothing.
    assert calendar_feed_service.render_feed(first_file_name) is not None
    assert_no_error_reported(bot)


async def test_new_link_replaces_the_old_one(node_handler, data_access, bot, calendar_feed_service):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    await drive_callback(node_handler, PLAYER_ID, 'CAL#S')
    old_file_name = _issued_file_name(_last_message(bot, PLAYER_ID))

    await drive_callback(node_handler, PLAYER_ID, 'CAL#R')

    new_file_name = _issued_file_name(_last_message(bot, PLAYER_ID))
    assert new_file_name != old_file_name
    assert calendar_feed_service.render_feed(old_file_name) is None
    assert calendar_feed_service.render_feed(new_file_name) is not None
    assert_no_error_reported(bot)


async def test_spectator_gets_a_link_too(node_handler, data_access, bot):
    seed_user(data_access, SPECTATOR_ID, Role.SPECTATOR, UserState.DEFAULT)

    await drive_callback(node_handler, SPECTATOR_ID, 'CAL#S')

    _issued_file_name(_last_message(bot, SPECTATOR_ID))
    assert_no_error_reported(bot)


async def test_inactive_member_cannot_use_the_button(node_handler, data_access, bot):
    inactive = seed_user(data_access, INACTIVE_ID, Role.INACTIVE, UserState.DEFAULT)

    update = await drive_callback(node_handler, INACTIVE_ID, 'CAL#S')

    assert update.callback_query.answered
    assert bot.texts_to(INACTIVE_ID) == []
    assert data_access.get_calendar_token(inactive.user_id) is None


async def test_inactive_admin_keeps_the_button_like_the_events_menu(node_handler, data_access, bot,
                                                                    calendar_feed_service):
    # Audience.EVERYONE includes every admin regardless of role - same gate as the events menu.
    seed_user(data_access, INACTIVE_ID, Role.INACTIVE, UserState.DEFAULT, is_admin=True)

    update = await drive_callback(node_handler, INACTIVE_ID, 'CAL#S')

    assert update.callback_query.answered
    file_name = _issued_file_name(_last_message(bot, INACTIVE_ID))
    assert calendar_feed_service.render_feed(file_name).startswith('BEGIN:VCALENDAR')
    assert_no_error_reported(bot)


async def test_failing_tap_is_reported_without_the_tapped_message(node_handler, data_access, bot, services,
                                                                  calendar_feed_service, monkeypatch):
    # The tapped message is the DM with the raw link; NodeHandler's report would carry str(update).
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    reported_updates = []
    original_report = services['telegram_service'].report_exception

    async def spy(description, error, update=None):
        reported_updates.append(update)
        await original_report(description, error, update)

    def broken_issue_link(_telegram_id):
        raise RuntimeError('db hiccup')

    monkeypatch.setattr(services['telegram_service'], 'report_exception', spy)
    monkeypatch.setattr(calendar_feed_service, 'issue_link', broken_issue_link)

    update = await drive_callback(node_handler, PLAYER_ID, 'CAL#R',
                                  message_text='<code>http://test.local/cal/x.ics</code>')

    assert update.callback_query.answered
    assert reported_updates == [None]
    assert any('db hiccup' in text for text in _maintainer_texts(bot))
    assert bot.texts_to(PLAYER_ID) == ['Something went wrong - please try again, the maintainer has been notified :)']


async def test_undeliverable_link_never_reaches_the_maintainer(node_handler, data_access, bot, caplog):
    member = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    forbid_chat(bot, PLAYER_ID)  # the member blocked the bot

    with caplog.at_level(logging.WARNING):
        await drive_callback(node_handler, PLAYER_ID, 'CAL#S')

    assert f'Could not deliver the calendar link to {PLAYER_ID}' in caplog.text
    assert data_access.get_calendar_token(member.user_id) is not None
    assert not any('/cal/' in text for text in _maintainer_texts(bot))
    assert_no_error_reported(bot)


async def test_removed_member_link_stops_working(node_handler, data_access, bot, services, calendar_feed_service):
    member = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    await drive_callback(node_handler, PLAYER_ID, 'CAL#S')
    file_name = _issued_file_name(_last_message(bot, PLAYER_ID))

    services['role_service'].remove_user(member.user_id)

    assert calendar_feed_service.render_feed(file_name) is None


# --- /calendar ---------------------------------------------------------------------------

async def test_calendar_command_in_private_chat(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, '/calendar')

    _issued_file_name(_last_message(bot, PLAYER_ID))
    assert_no_error_reported(bot)


async def test_calendar_command_in_a_group_issues_nothing(node_handler, data_access, bot):
    # Groups are dropped before any node runs, so a link can never land in a group.
    member = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive_group(node_handler, GROUP_CHAT_ID, PLAYER_ID, '/calendar')

    assert bot.sent == []
    assert data_access.get_calendar_token(member.user_id) is None


async def test_calendar_command_while_the_feature_is_off(node_handler_feature_off, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler_feature_off, PLAYER_ID, '/calendar')

    assert bot.texts_to(PLAYER_ID)[-1] == 'The calendar subscription is not set up on this bot.'
    assert_no_error_reported(bot)


async def test_calendar_command_is_listed_in_help(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, '/help')

    assert '/calendar' in bot.texts_to(PLAYER_ID)[-1]
