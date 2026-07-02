"""The low-availability game trigger.

Counts availability over all active players: yes + unsure (active players
without an answer default to unsure). Once cancellations leave at most
MAX_PLAYERS_PER_GAME available, a NO update notifies the game trainers.
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from domain.GameRules import MAX_PLAYERS_PER_GAME
from domain.entities.Game import Game
from domain.entities.Attendance import Attendance
from domain.EventDateTimeParser import parse
from framework.Triggers.TriggerPayload import TriggerPayload
from tests.helpers import seed_user

FIRST_PLAYER_ID = 1500
ACTIVE_PLAYERS = MAX_PLAYERS_PER_GAME + 3


@pytest.fixture
def game(data_access):
    return data_access.add(Game(parse("24.12.2030 18:30").value, "home arena", "rivals fc"))


@pytest.fixture
def player_ids(data_access):
    return [seed_user(data_access, FIRST_PLAYER_ID + n, Role.PLAYER, UserState.DEFAULT).user_id
            for n in range(ACTIVE_PLAYERS)]


def _say_no(data_access, player_ids, game, count) -> Attendance:
    for player_id in player_ids[:count]:
        attendance = data_access.update_attendance(
            Attendance(player_id, game.doc_id, AttendanceState.NO), Event.GAME)
    return attendance


def _trainer_texts(bot, api_config):
    trainer_chat_id = api_config.get_int_list('Chat_Ids', 'TRAINERS_GAMES')[0]
    return bot.texts_to(trainer_chat_id)


async def test_fires_once_only_max_players_stay_available(services, data_access, api_config, bot, game, player_ids):
    last_no = _say_no(data_access, player_ids, game, count=3)   # 12 active - 3 no = 9 available

    payload = TriggerPayload(new_attendance=last_no, doc_id=game.doc_id, event_type=Event.GAME)
    await services["trigger_service"].check_triggers(payload)

    texts = _trainer_texts(bot, api_config)
    assert any(f'at most {MAX_PLAYERS_PER_GAME} players' in text and '24.12.2030 18:30' in text
               for text in texts)


async def test_silent_while_more_than_max_players_available(services, data_access, api_config, bot, game, player_ids):
    last_no = _say_no(data_access, player_ids, game, count=2)   # 12 active - 2 no = 10 available

    payload = TriggerPayload(new_attendance=last_no, doc_id=game.doc_id, event_type=Event.GAME)
    await services["trigger_service"].check_triggers(payload)

    assert _trainer_texts(bot, api_config) == []


async def test_yes_update_never_fires(services, data_access, api_config, bot, game, player_ids):
    _say_no(data_access, player_ids, game, count=3)             # availability already at the limit
    yes = data_access.update_attendance(
        Attendance(player_ids[-1], game.doc_id, AttendanceState.YES), Event.GAME)

    payload = TriggerPayload(new_attendance=yes, doc_id=game.doc_id, event_type=Event.GAME)
    await services["trigger_service"].check_triggers(payload)

    assert _trainer_texts(bot, api_config) == []
