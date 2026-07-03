"""The low-availability game trigger.

Availability = yes + unsure: every active player counts (no answer defaults to
unsure), plus anyone — even retired/inactive — who explicitly said yes. While
cancellations leave at most MAX_PLAYERS_PER_GAME available, every NO update
notifies the game trainers with the current count.
"""
import pytest

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from domain.GameRules import MAX_PLAYERS_PER_GAME
from framework.Triggers.TriggerPayload import TriggerPayload
from tests.helpers import seed_user, set_attendance

FIRST_PLAYER_ID = 1500
ACTIVE_PLAYERS = MAX_PLAYERS_PER_GAME + 3


@pytest.fixture
def player_ids(data_access):
    return [seed_user(data_access, FIRST_PLAYER_ID + n, Role.PLAYER, UserState.DEFAULT).user_id
            for n in range(ACTIVE_PLAYERS)]


def _say_no(data_access, player_ids, game, count) -> TriggerPayload:
    attendances = [set_attendance(data_access, player_id, game.doc_id, AttendanceState.NO)
                   for player_id in player_ids[:count]]
    return TriggerPayload(new_attendance=attendances[-1], doc_id=game.doc_id, event_type=Event.GAME)


def _trainer_texts(bot, default_team):
    trainer_chat_id = default_team.trainers_games[0]
    return bot.texts_to(trainer_chat_id)


async def test_fires_when_at_most_max_players_stay_available(services, data_access, bot, game, player_ids,
                                                             default_team):
    payload = _say_no(data_access, player_ids, game, count=3)   # 12 active - 3 no = 9 available

    await services["trigger_service"].check_triggers(payload)

    texts = _trainer_texts(bot, default_team)
    assert any(f'only {MAX_PLAYERS_PER_GAME} players' in text and '24.12.2030 18:30' in text
               for text in texts)


async def test_fires_again_on_every_further_no_with_current_count(services, data_access, bot, game, player_ids,
                                                                  default_team):
    for count in [3, 4]:                                        # 9 available, then 8
        payload = _say_no(data_access, player_ids, game, count=count)
        await services["trigger_service"].check_triggers(payload)

    texts = _trainer_texts(bot, default_team)
    assert len(texts) == 2
    assert 'only 9 players' in texts[0]
    assert 'only 8 players' in texts[1]


async def test_silent_while_more_than_max_players_available(services, data_access, bot, game, player_ids,
                                                            default_team):
    payload = _say_no(data_access, player_ids, game, count=2)   # 12 active - 2 no = 10 available

    await services["trigger_service"].check_triggers(payload)

    assert _trainer_texts(bot, default_team) == []


async def test_yes_update_never_fires(services, data_access, bot, game, player_ids, default_team):
    _say_no(data_access, player_ids, game, count=3)             # availability already at the limit
    yes = set_attendance(data_access, player_ids[-1], game.doc_id, AttendanceState.YES)

    payload = TriggerPayload(new_attendance=yes, doc_id=game.doc_id, event_type=Event.GAME)
    await services["trigger_service"].check_triggers(payload)

    assert _trainer_texts(bot, default_team) == []


async def test_retired_player_who_said_yes_counts_as_available(services, data_access, bot, game, player_ids,
                                                               default_team):
    retired = seed_user(data_access, FIRST_PLAYER_ID + 100, Role.RETIRED, UserState.DEFAULT)
    set_attendance(data_access, retired.user_id, game.doc_id, AttendanceState.YES)
    payload = _say_no(data_access, player_ids, game, count=3)   # 9 active open + 1 retired yes = 10

    await services["trigger_service"].check_triggers(payload)

    assert _trainer_texts(bot, default_team) == []
