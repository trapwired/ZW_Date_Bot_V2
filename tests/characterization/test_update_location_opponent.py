"""Characterization: editing an existing event's location / opponent.

Text-driven (fallback -> handle_event_field), so the user is seeded directly into
the single field-edit state (ADMIN_UPDATE_EVENT_FIELD) with the event-card context,
event type, and field stashed in additional_info, as the card's field button would
leave it. Persistence runs through EventService.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.EventField import EventField
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


async def test_update_location_persists_and_returns_to_main_menu(node_handler, data_access, bot):
    game = _seed_game_and_state(data_access, EventField.LOCATION)

    await drive(node_handler, ADMIN_ID, "New Stadium")

    assert data_access.get_game(game.doc_id).location == "new stadium"
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert data_access.get_user_state(ADMIN_ID).additional_info == ''
    assert_no_error_reported(bot)


async def test_update_opponent_persists(node_handler, data_access, bot):
    game = _seed_game_and_state(data_access, EventField.OPPONENT)

    await drive(node_handler, ADMIN_ID, "New Rivals")

    assert data_access.get_game(game.doc_id).opponent == "new rivals"
    assert current_state(data_access, ADMIN_ID) == UserState.DEFAULT
    assert_no_error_reported(bot)


async def test_update_refreshes_the_event_card_message(node_handler, data_access, bot):
    _seed_game_and_state(data_access, EventField.LOCATION)

    await drive(node_handler, ADMIN_ID, "New Stadium")

    # The originating card message (message_id 1 in the stashed context) was re-rendered.
    assert any(e.message_id == 1 and "New Stadium" in e.text for e in bot.edits)
    assert_no_error_reported(bot)
