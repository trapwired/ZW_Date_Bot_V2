"""Characterization: the admin add-event wizard for all three event types.

The wizard starts from the admin menu's inline chooser (AP#A#<type>) and runs on the
single ADMIN_ADD_EVENT state; the event type and current field live in the draft
(TempData.step: DATETIME -> LOCATION -> [OPPONENT] -> SAVE), so the assertions pin
both the state and the step. The buttons on the draft message (save/restart/cancel)
are covered here too.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.EventField import EventField
from features.adminpanel import AdminMenu
from tests.helpers import drive, drive_callback, seed_user, current_state, current_step, assert_no_error_reported

ADMIN_ID = 500
FUTURE_TIMESTAMP = "24.12.2030 18:30"


def _start(event_type: Event) -> str:
    return AdminMenu.encode(AdminMenu.ADD_CHOOSER, int(event_type))


async def test_add_game_full_navigation_and_persist(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID, _start(Event.GAME))
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT
    assert current_step(data_access, ADMIN_ID) == EventField.DATETIME

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_step(data_access, ADMIN_ID) == EventField.LOCATION

    await drive(node_handler, ADMIN_ID, "Home Arena")
    assert current_step(data_access, ADMIN_ID) == EventField.OPPONENT

    await drive(node_handler, ADMIN_ID, "Rivals FC")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT
    assert current_step(data_access, ADMIN_ID) == EventField.SAVE

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT

    games = data_access.get_ordered_games()
    assert len(games) == 1
    assert games[0].location == "home arena"
    assert games[0].opponent == "rivals fc"
    assert (games[0].timestamp.year, games[0].timestamp.month, games[0].timestamp.day) == (2030, 12, 24)
    assert_no_error_reported(bot)


async def test_add_training_has_no_opponent_step(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID, _start(Event.TRAINING))
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT
    assert current_step(data_access, ADMIN_ID) == EventField.DATETIME

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_step(data_access, ADMIN_ID) == EventField.LOCATION

    # No opponent step for trainings: location goes straight to the finish (SAVE) step.
    await drive(node_handler, ADMIN_ID, "Sporthalle")
    assert current_step(data_access, ADMIN_ID) == EventField.SAVE

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT

    trainings = data_access.get_ordered_trainings()
    assert len(trainings) == 1
    assert trainings[0].location == "sporthalle"
    assert_no_error_reported(bot)


async def test_add_timekeeping_persists(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID, _start(Event.TIMEKEEPING))
    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    await drive(node_handler, ADMIN_ID, "Eventhalle")
    await drive(node_handler, ADMIN_ID, "save")

    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    timekeepings = data_access.get_ordered_timekeepings()
    assert len(timekeepings) == 1
    assert timekeepings[0].location == "eventhalle"
    assert_no_error_reported(bot)


async def test_past_timestamp_is_rejected_and_stays_on_step(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID, _start(Event.GAME))
    await drive(node_handler, ADMIN_ID, "1.1.2020 12:00")  # in the past

    # Stays on the timestamp step; nothing advances, nothing saved.
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT
    assert current_step(data_access, ADMIN_ID) == EventField.DATETIME
    assert any("past" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_cancel_during_wizard_returns_to_main_menu(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID, _start(Event.GAME))
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT

    await drive(node_handler, ADMIN_ID, "/cancel")
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert data_access.get_ordered_games() == []
    assert_no_error_reported(bot)


async def test_save_button_commits_finished_draft(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.TRAINING))
    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    await drive(node_handler, ADMIN_ID, "Sporthalle")

    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WIZARD_SAVE))

    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert len(data_access.get_ordered_trainings()) == 1
    assert_no_error_reported(bot)


async def test_restart_button_starts_a_fresh_draft(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.TRAINING))
    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_step(data_access, ADMIN_ID) == EventField.LOCATION

    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WIZARD_RESTART))

    # Back at the wizard start with a fresh draft of the same type.
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_EVENT
    assert current_step(data_access, ADMIN_ID) == EventField.DATETIME
    assert_no_error_reported(bot)


async def test_cancel_button_discards_draft(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.GAME))

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WIZARD_CANCEL))

    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert data_access.get_ordered_games() == []
    assert any("Cancelled" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_second_wizard_start_replaces_the_first_draft(node_handler, data_access, bot):
    # Starting the wizard from two admin-menu messages must not leave two drafts behind
    # (a second TempData row would make every get_draft lookup fail from then on).
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.GAME))
    await drive_callback(node_handler, ADMIN_ID, _start(Event.TRAINING))

    # The wizard continues on the fresh (training) draft; typed input still works.
    assert current_step(data_access, ADMIN_ID) == EventField.DATETIME
    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    await drive(node_handler, ADMIN_ID, "Sporthalle")
    await drive(node_handler, ADMIN_ID, "save")

    assert len(data_access.get_ordered_trainings()) == 1
    assert data_access.get_ordered_games() == []
    assert_no_error_reported(bot)


async def test_stale_wizard_button_after_cancel_degrades_gracefully(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.GAME))
    await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WIZARD_CANCEL))

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.WIZARD_SAVE))

    assert any("no longer active" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_consumed_prompts_are_deleted(node_handler, data_access, bot):
    # Each accepted input deletes the previous 'Send me the ...' prompt; saving deletes
    # the last one, so no consumed prompt is left in the chat.
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.TRAINING))
    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    await drive(node_handler, ADMIN_ID, "Sporthalle")
    await drive(node_handler, ADMIN_ID, "save")

    prompt_ids = [m.message_id for m in bot.sent if "Send me the new" in m.text or "SAVE" in m.text]
    assert len(prompt_ids) == 3                      # datetime, location, finish instructions
    assert sorted(m.message_id for m in bot.deleted) == sorted(prompt_ids)
    assert_no_error_reported(bot)


async def test_wizard_markup_offers_save_only_on_finish_step(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    await drive_callback(node_handler, ADMIN_ID, _start(Event.TRAINING))

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    mid_wizard = [b.callback_data for row in bot.edits[-1].reply_markup.inline_keyboard for b in row]
    assert AdminMenu.encode(AdminMenu.WIZARD_SAVE) not in mid_wizard

    await drive(node_handler, ADMIN_ID, "Sporthalle")
    finish_step = [b.callback_data for row in bot.edits[-1].reply_markup.inline_keyboard for b in row]
    assert AdminMenu.encode(AdminMenu.WIZARD_SAVE) in finish_step
    assert AdminMenu.encode(AdminMenu.WIZARD_CANCEL) in finish_step
    assert_no_error_reported(bot)
