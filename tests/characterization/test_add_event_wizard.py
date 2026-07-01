"""Characterization: the admin add-event wizard for all three event types.

This is the most duplicated, most stateful flow (AddEventFieldsNode). The wizard
runs on a single per-type state (ADMIN_ADD_GAME etc.) and the current
field is held in the draft (TempData.step: DATETIME -> LOCATION -> [OPPONENT] -> SAVE),
so the assertions pin both the state and the step.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.CallbackOption import CallbackOption
from tests.helpers import drive, seed_user, current_state, current_step, assert_no_error_reported

ADMIN_ID = 500
FUTURE_TIMESTAMP = "24.12.2030 18:30"


async def test_add_game_full_navigation_and_persist(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive(node_handler, ADMIN_ID, "/admin")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    await drive(node_handler, ADMIN_ID, "/add")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD

    await drive(node_handler, ADMIN_ID, "/game")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME
    assert current_step(data_access, ADMIN_ID) == CallbackOption.DATETIME

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_step(data_access, ADMIN_ID) == CallbackOption.LOCATION

    await drive(node_handler, ADMIN_ID, "Home Arena")
    assert current_step(data_access, ADMIN_ID) == CallbackOption.OPPONENT

    await drive(node_handler, ADMIN_ID, "Rivals FC")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME
    assert current_step(data_access, ADMIN_ID) == CallbackOption.SAVE

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    games = data_access.get_ordered_games()
    assert len(games) == 1
    assert games[0].location == "home arena"
    assert games[0].opponent == "rivals fc"
    assert (games[0].timestamp.year, games[0].timestamp.month, games[0].timestamp.day) == (2030, 12, 24)
    assert_no_error_reported(bot)


async def test_add_training_has_no_opponent_step(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, "/training")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_TRAINING
    assert current_step(data_access, ADMIN_ID) == CallbackOption.DATETIME

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_step(data_access, ADMIN_ID) == CallbackOption.LOCATION

    # No opponent step for trainings: location goes straight to the finish (SAVE) step.
    await drive(node_handler, ADMIN_ID, "Sporthalle")
    assert current_step(data_access, ADMIN_ID) == CallbackOption.SAVE

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    trainings = data_access.get_ordered_trainings()
    assert len(trainings) == 1
    assert trainings[0].location == "sporthalle"
    assert_no_error_reported(bot)


async def test_add_timekeeping_persists(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, "/timekeeping")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_TIMEKEEPING
    assert current_step(data_access, ADMIN_ID) == CallbackOption.DATETIME

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_step(data_access, ADMIN_ID) == CallbackOption.LOCATION

    await drive(node_handler, ADMIN_ID, "Eventhalle")
    assert current_step(data_access, ADMIN_ID) == CallbackOption.SAVE

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    timekeepings = data_access.get_ordered_timekeepings()
    assert len(timekeepings) == 1
    assert timekeepings[0].location == "eventhalle"
    assert_no_error_reported(bot)


async def test_past_timestamp_is_rejected_and_stays_on_step(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, "/game")
    await drive(node_handler, ADMIN_ID, "1.1.2020 12:00")  # in the past

    # Stays on the timestamp step; nothing advances, nothing saved.
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME
    assert current_step(data_access, ADMIN_ID) == CallbackOption.DATETIME
    assert any("past" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_cancel_during_wizard_returns_to_admin(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, "/game")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME

    await drive(node_handler, ADMIN_ID, "/cancel")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert data_access.get_ordered_games() == []
    assert_no_error_reported(bot)
