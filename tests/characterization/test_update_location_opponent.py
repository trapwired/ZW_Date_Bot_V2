"""Characterization: editing an existing event's location / opponent.

Text-driven (handle_help -> handle_event_location_or_opponent), so the user is
seeded directly into the field-edit state with the inline-message context in
additional_info, as the update callback step would leave it. Pins the flow
before Phase 2b routes its persistence through EventService.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from databaseEntities.Game import Game
from Utils import CallbackUtils
from domain.EventDateTimeParser import parse
from tests.helpers import drive, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 900
FUTURE = "24.12.2030 18:30"


def _seed_game_and_state(data_access, edit_state):
    game = data_access.add(Game(parse(FUTURE).value, "old arena", "old opponent"))
    seed_user(data_access, ADMIN_ID, Role.ADMIN, edit_state,
              additional_info=CallbackUtils.build_additional_information(1, ADMIN_ID, game.doc_id))
    return game


async def test_update_location_persists_and_returns_to_admin(node_handler, data_access, bot):
    game = _seed_game_and_state(data_access, UserState.ADMIN_UPDATE_GAME_LOCATION)

    await drive(node_handler, ADMIN_ID, "New Stadium")

    assert data_access.get_game(game.doc_id).location == "new stadium"
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)


async def test_update_opponent_persists(node_handler, data_access, bot):
    game = _seed_game_and_state(data_access, UserState.ADMIN_UPDATE_GAME_OPPONENT)

    await drive(node_handler, ADMIN_ID, "New Rivals")

    assert data_access.get_game(game.doc_id).opponent == "new rivals"
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)
