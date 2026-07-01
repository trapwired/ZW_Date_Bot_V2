"""Characterization: editing an existing event's location / opponent.

Text-driven (handle_help -> handle_event_field), so the user is seeded directly into
the single field-edit state (ADMIN_UPDATE_EVENT_FIELD) with the inline-message context,
event type, and field stashed in additional_info, as the update callback step would
leave it. Persistence runs through EventService.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from domain.entities.Game import Game
from Utils import CallbackUtils
from domain.EventDateTimeParser import parse
from tests.helpers import drive, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 900
FUTURE = "24.12.2030 18:30"


def _seed_game_and_state(data_access, field):
    game = data_access.add(Game(parse(FUTURE).value, "old arena", "old opponent"))
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_EVENT_FIELD,
              additional_info=CallbackUtils.build_additional_information(1, ADMIN_ID, game.doc_id, Event.GAME, field))
    return game


async def test_update_location_persists_and_returns_to_admin(node_handler, data_access, bot):
    game = _seed_game_and_state(data_access, CallbackOption.LOCATION)

    await drive(node_handler, ADMIN_ID, "New Stadium")

    assert data_access.get_game(game.doc_id).location == "new stadium"
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)


async def test_update_opponent_persists(node_handler, data_access, bot):
    game = _seed_game_and_state(data_access, CallbackOption.OPPONENT)

    await drive(node_handler, ADMIN_ID, "New Rivals")

    assert data_access.get_game(game.doc_id).opponent == "new rivals"
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)
