"""Characterization: the admin actions on the event card (edit fields, delete).

Admins get an extra [Edit event][Delete event] row on the card; the whole flow stays
on the one inline message. Deleting asks for confirmation; picking a field hands over
to the typed-input state (ADMIN_UPDATE_EVENT_FIELD).
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.EventField import EventField
from domain.entities.Training import Training
from features.events import EventsMenu
from Utils import CallbackUtils
from Utils.CustomExceptions import ObjectNotFoundException
from domain.EventDateTimeParser import parse
from tests.helpers import drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 1000
PLAYER_ID = 1001
FUTURE = "24.12.2030 18:30"


def _buttons(reply_markup):
    return [button for row in reply_markup.inline_keyboard for button in row]


async def test_admin_card_has_edit_and_delete_row(node_handler, data_access, bot, game):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, EventsMenu.encode_card(Event.GAME, game.doc_id))

    data = [b.callback_data for b in _buttons(update.callback_query.edits[-1].reply_markup)]
    assert EventsMenu.encode_edit_fields(Event.GAME, game.doc_id) in data
    assert EventsMenu.encode_delete(Event.GAME, game.doc_id) in data
    assert_no_error_reported(bot)


async def test_player_card_has_no_admin_row(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID, EventsMenu.encode_card(Event.GAME, game.doc_id))

    data = [b.callback_data for b in _buttons(update.callback_query.edits[-1].reply_markup)]
    assert not any(d.startswith("EV#E") or d.startswith("EV#D") for d in data)
    assert_no_error_reported(bot)


async def test_delete_asks_for_confirmation_then_deletes(node_handler, data_access, bot, game):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, EventsMenu.encode_delete(Event.GAME, game.doc_id))
    edit = update.callback_query.edits[-1]
    assert "Really delete" in edit.text
    assert EventsMenu.encode_delete_confirmed(Event.GAME, game.doc_id) in \
        [b.callback_data for b in _buttons(edit.reply_markup)]

    update = await drive_callback(node_handler, ADMIN_ID,
                                  EventsMenu.encode_delete_confirmed(Event.GAME, game.doc_id))
    with pytest.raises(ObjectNotFoundException):
        data_access.get_game(game.doc_id)
    assert any("Deleted" in e.text for e in update.callback_query.edits)
    assert_no_error_reported(bot)


async def test_player_pressing_forwarded_delete_button_changes_nothing(node_handler, data_access, bot, game):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    update = await drive_callback(node_handler, PLAYER_ID,
                                  EventsMenu.encode_delete_confirmed(Event.GAME, game.doc_id))

    assert data_access.get_game(game.doc_id) is not None
    assert update.callback_query.answered
    assert not update.callback_query.edits
    assert_no_error_reported(bot)


async def test_edit_shows_field_chooser_per_event_type(node_handler, data_access, bot, game):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    training = data_access.add(Training(parse(FUTURE).value, "sporthalle"))

    update = await drive_callback(node_handler, ADMIN_ID, EventsMenu.encode_edit_fields(Event.GAME, game.doc_id))
    game_fields = [b.callback_data for b in _buttons(update.callback_query.edits[-1].reply_markup)]
    assert EventsMenu.encode_edit_field(Event.GAME, game.doc_id, EventField.OPPONENT) in game_fields

    update = await drive_callback(node_handler, ADMIN_ID,
                                  EventsMenu.encode_edit_fields(Event.TRAINING, training.doc_id))
    training_fields = [b.callback_data for b in _buttons(update.callback_query.edits[-1].reply_markup)]
    # Only games have an opponent: the chooser never offers it for a training.
    assert not any(f'#{int(EventField.OPPONENT)}' == d[-3:] for d in training_fields)
    assert_no_error_reported(bot)


async def test_picking_a_field_hands_over_to_typed_input(node_handler, data_access, bot, game):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID,
                         EventsMenu.encode_edit_field(Event.GAME, game.doc_id, EventField.LOCATION),
                         message_id=77)

    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_UPDATE_EVENT_FIELD
    edit_context = CallbackUtils.try_parse_additional_information(
        data_access.get_user_state(ADMIN_ID).additional_info)
    assert edit_context == (77, ADMIN_ID, game.doc_id, Event.GAME, EventField.LOCATION)
    assert any("Location" in m.text for m in bot.sent)   # typed-input prompt went out
    assert_no_error_reported(bot)
