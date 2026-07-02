"""Characterization: the inline events menu (list -> card) for players and spectators.

The 'events' keyboard entry sends an inline event list; tapping an event edits the
same message into the event card. Role differences: spectators never see timekeeping
events and get a read-only card; players see their own status in the list and can
set attendance on the card.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from domain.entities.Training import Training
from domain.entities.TimekeepingEvent import TimekeepingEvent
from features.events import EventsMenu
from domain.EventDateTimeParser import parse
from tests.helpers import (drive, drive_callback, seed_user, set_attendance,
                           assert_no_error_reported)

PLAYER_ID = 2100
SPECTATOR_ID = 2101
FUTURE = "24.12.2030 18:30"


def _buttons(reply_markup):
    return [button for row in reply_markup.inline_keyboard for button in row]


def _last_markup(bot, chat_id):
    return [m for m in bot.sent if m.chat_id == chat_id][-1].reply_markup


async def test_events_entry_sends_event_list_with_card_buttons(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "Events")

    buttons = _buttons(_last_markup(bot, PLAYER_ID))
    assert [b.callback_data for b in buttons] == [EventsMenu.encode_card(Event.GAME, game.doc_id)]
    assert_no_error_reported(bot)


async def test_event_list_shows_own_attendance_prefix(node_handler, data_access, bot, game):
    uts = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    set_attendance(data_access, uts.user_id, game.doc_id, AttendanceState.YES)

    await drive(node_handler, PLAYER_ID, "events")

    (button,) = _buttons(_last_markup(bot, PLAYER_ID))
    assert button.text.startswith("✅")
    assert_no_error_reported(bot)


async def test_event_list_filter_row_hides_timekeeping_from_spectators(node_handler, data_access, bot, game):
    data_access.add(TimekeepingEvent(parse(FUTURE).value, "eventhalle"))
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    seed_user(data_access, SPECTATOR_ID, Role.SPECTATOR, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "events")
    player_filters = [b.callback_data for b in _buttons(_last_markup(bot, PLAYER_ID))]
    assert EventsMenu.encode_list(Event.TIMEKEEPING) in player_filters

    await drive(node_handler, SPECTATOR_ID, "events")
    spectator_markup = _last_markup(bot, SPECTATOR_ID)
    spectator_data = [b.callback_data for b in _buttons(spectator_markup)]
    assert EventsMenu.encode_list(Event.TIMEKEEPING) not in spectator_data
    # And the spectator's list rows carry no attendance prefix.
    card_buttons = [b for b in _buttons(spectator_markup) if b.callback_data.startswith("EV#C")]
    assert card_buttons and not card_buttons[0].text.startswith(("✅", "❌", "❓"))
    assert_no_error_reported(bot)


async def test_no_upcoming_events_message(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "events")

    assert any("no upcoming events" in m.text.lower() for m in bot.sent)
    assert_no_error_reported(bot)


async def test_card_shows_summary_and_attendance_buttons_for_player(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_card(Event.GAME, game.doc_id))

    edit = update.callback_query.edits[-1]
    assert "Rivals Fc" in edit.text                      # game details incl. opponent
    assert "Your answer" in edit.text
    data = [b.callback_data for b in _buttons(edit.reply_markup)]
    assert EventsMenu.encode_attend(Event.GAME, game.doc_id, AttendanceState.YES) in data
    assert EventsMenu.encode_list(Event.GAME) in data    # back to list
    assert_no_error_reported(bot)


async def test_card_is_read_only_for_spectators(node_handler, data_access, bot, game):
    seed_user(data_access, SPECTATOR_ID, Role.SPECTATOR, UserState.DEFAULT)

    update = await drive_callback(node_handler, SPECTATOR_ID, EventsMenu.encode_card(Event.GAME, game.doc_id))

    edit = update.callback_query.edits[-1]
    data = [b.callback_data for b in _buttons(edit.reply_markup)]
    assert not any(d.startswith("EV#A") for d in data)   # no attendance buttons
    assert not any(d.startswith("EV#E") or d.startswith("EV#D") for d in data)  # no admin row
    assert EventsMenu.encode_calendar(Event.GAME, game.doc_id) in data
    assert_no_error_reported(bot)


async def test_full_timekeeping_card_locks_out_non_yes_players(node_handler, data_access, bot):
    tke = data_access.add(TimekeepingEvent(parse(FUTURE).value, "eventhalle", people_required=1))
    helper = seed_user(data_access, 2102, Role.PLAYER, UserState.DEFAULT)
    set_attendance(data_access, helper.user_id, tke.doc_id, AttendanceState.YES, Event.TIMEKEEPING)
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_card(Event.TIMEKEEPING, tke.doc_id))

    edit = update.callback_query.edits[-1]
    assert "enough people" in edit.text
    assert not any(b.callback_data.startswith("EV#A") for b in _buttons(edit.reply_markup))
    assert_no_error_reported(bot)


async def test_card_of_deleted_event_degrades_gracefully(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    data_access.delete_event(Event.GAME, game.doc_id)

    update = await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_card(Event.GAME, game.doc_id))

    assert any("no longer exists" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_long_event_list_paginates(node_handler, data_access, bot):
    from domain.entities.Game import Game
    for day in range(1, 11):     # 10 games -> pages of 8 + 2
        data_access.add(Game(parse(f"{day:02d}.12.2030 18:30").value, f"arena {day}", "rivals fc"))
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, "events")
    first_page = _buttons(_last_markup(bot, PLAYER_ID))
    card_buttons = [b for b in first_page if b.callback_data.startswith("EV#C")]
    assert len(card_buttons) == 8
    assert EventsMenu.encode_list(Event.GAME, 1) in [b.callback_data for b in first_page]  # 'more »'

    update = await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_list(Event.GAME, 1))
    second_page = _buttons(update.callback_query.edits[-1].reply_markup)
    assert len([b for b in second_page if b.callback_data.startswith("EV#C")]) == 2
    assert EventsMenu.encode_list(Event.GAME) in [b.callback_data for b in second_page]    # '« previous'
    assert_no_error_reported(bot)


async def test_list_navigation_between_types(node_handler, data_access, bot, game):
    training = data_access.add(Training(parse(FUTURE).value, "sporthalle"))
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_list(Event.TRAINING))

    edit = update.callback_query.edits[-1]
    data = [b.callback_data for b in _buttons(edit.reply_markup)]
    assert EventsMenu.encode_card(Event.TRAINING, training.doc_id) in data
    assert EventsMenu.encode_card(Event.GAME, game.doc_id) not in data
    assert_no_error_reported(bot)
