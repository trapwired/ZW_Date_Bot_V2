"""Characterization: the callback-driven event flows (delete, add cancel/save).

Pins UpdateEventCallbackNode and AddEventCallbackNode before Phase 2b-ii routes
their persistence through EventService. Driven via the callback-query harness.
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from domain.entities.Game import Game
from domain.entities.Training import Training
from domain.entities.TempData import TempData
from Utils import CallbackUtils
from Utils.CustomExceptions import ObjectNotFoundException, NoTempDataFoundException
from domain.EventDateTimeParser import parse
from tests.helpers import (drive_callback, make_callback_update, seed_user, current_state,
                           assert_no_error_reported)

ADMIN_ID = 1000
FUTURE = "24.12.2030 18:30"


def _cb(user_state, event, option, doc_id):
    return CallbackUtils.get_callback_message(user_state, event, option, doc_id)


async def test_delete_game_callback_removes_the_event(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE_GAME)
    game = data_access.add(Game(parse(FUTURE).value, "home arena", "rivals fc"))

    # Confirm-delete (the YES on the delete confirmation).
    await drive_callback(node_handler, ADMIN_ID,
                         _cb(UserState.ADMIN_UPDATE, Event.GAME, CallbackOption.YES, game.doc_id))

    with pytest.raises(ObjectNotFoundException):
        data_access.get_game(game.doc_id)
    assert assert_no_error_reported(bot) is None


async def test_add_cancel_callback_discards_draft(node_handler, data_access, bot):
    uts = seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD_GAME)
    draft = data_access.add(TempData(uts.user_id, Event.GAME, chat_id=ADMIN_ID, query_id=10))

    await drive_callback(node_handler, ADMIN_ID,
                         _cb(UserState.ADMIN_ADD_GAME, Event.GAME, CallbackOption.CANCEL, draft.doc_id))

    with pytest.raises(NoTempDataFoundException):
        data_access.get_temp_data(uts.user_id)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)


async def test_add_save_callback_creates_event_and_clears_draft(node_handler, data_access, bot):
    uts = seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_ADD_GAME)
    draft = data_access.add(TempData(uts.user_id, Event.GAME, timestamp=parse(FUTURE).value,
                                     location="home arena", opponent="rivals fc",
                                     step=CallbackOption.SAVE, chat_id=ADMIN_ID, query_id=10))

    await drive_callback(node_handler, ADMIN_ID,
                         _cb(UserState.ADMIN_ADD_GAME, Event.GAME, CallbackOption.SAVE, draft.doc_id))

    games = data_access.get_ordered_games()
    assert len(games) == 1
    assert games[0].location == "home arena"
    with pytest.raises(NoTempDataFoundException):
        data_access.get_temp_data(uts.user_id)
    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN
    assert_no_error_reported(bot)


async def test_opponent_edit_on_non_game_is_rejected(node_handler, data_access):
    # OPPONENT is only a game field; a training/timekeeping OPPONENT edit can only come from
    # a forged or stale callback. The node raises (NodeHandler turns that into a maintainer
    # alert in production) rather than transitioning into the edit state and later writing a
    # phantom attribute. Driven at the node so the assertion isn't the harness's maintainer
    # path (send_maintainer_message dispatches on a real telegram.Update, which the fake isn't).
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.ADMIN_UPDATE)
    training = data_access.add(Training(parse(FUTURE).value, "sporthalle"))

    update = make_callback_update(ADMIN_ID, _cb(UserState.ADMIN_UPDATE, Event.TRAINING,
                                                CallbackOption.OPPONENT, training.doc_id))
    callback_node = node_handler.get_callback_node(update)
    with pytest.raises(ValueError):
        await callback_node.handle(update)

    assert current_state(data_access, ADMIN_ID) == UserState.ADMIN_UPDATE  # no transition to the edit state
