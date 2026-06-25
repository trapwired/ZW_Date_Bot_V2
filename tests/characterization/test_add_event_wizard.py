"""Characterization: the admin add-event wizard for all three event types.

This is the most duplicated, most stateful flow (AddEventFieldsNode + the
ADMIN_ADD_*_{TIMESTAMP,LOCATION,OPPONENT,FINISH} state chain), so it is the
contract Phase 1 (de-dup) and Phase 3 (state collapse) must preserve exactly.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from tests.helpers import drive, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 500
FUTURE_TIMESTAMP = "24.12.2030 18:30"


async def test_add_game_full_navigation_and_persist(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive(node_handler, ADMIN_ID, "/admin")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    await drive(node_handler, ADMIN_ID, "/add")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD

    await drive(node_handler, ADMIN_ID, "/game")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME_TIMESTAMP

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME_LOCATION

    await drive(node_handler, ADMIN_ID, "Home Arena")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME_OPPONENT

    await drive(node_handler, ADMIN_ID, "Rivals FC")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_FINISH_ADD_GAME

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
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_TRAINING_TIMESTAMP

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_TRAINING_LOCATION

    # No opponent step for trainings: location goes straight to the finish state.
    await drive(node_handler, ADMIN_ID, "Sporthalle")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_FINISH_ADD_TRAINING

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    trainings = data_access.get_ordered_trainings()
    assert len(trainings) == 1
    assert trainings[0].location == "sporthalle"
    assert_no_error_reported(bot)


async def test_add_timekeeping_persists(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, "/timekeeping")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_TIMEKEEPING_TIMESTAMP

    await drive(node_handler, ADMIN_ID, FUTURE_TIMESTAMP)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_TIMEKEEPING_LOCATION

    await drive(node_handler, ADMIN_ID, "Eventhalle")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_FINISH_ADD_TIMEKEEPING

    await drive(node_handler, ADMIN_ID, "save")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN

    timekeepings = data_access.get_ordered_timekeepings()
    assert len(timekeepings) == 1
    assert timekeepings[0].location == "eventhalle"
    assert_no_error_reported(bot)


async def test_cancel_during_wizard_returns_to_admin(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD)

    await drive(node_handler, ADMIN_ID, "/game")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_ADD_GAME_TIMESTAMP

    await drive(node_handler, ADMIN_ID, "/cancel")
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert data_access.get_ordered_games() == []
    assert_no_error_reported(bot)
