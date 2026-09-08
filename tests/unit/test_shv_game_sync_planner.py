"""Unit: the SHV sync diff - what gets imported, what counts as the same game
(deciding factor: the opponent), and what is only reported, never touched."""
import pandas as pd

from domain.entities.Game import Game

from features.shvsync import GameSyncPlanner
from features.shvsync.ShvApiClient import ShvGame

from Utils import DateTimeUtils


def _ts(day: int, hour: int = 18) -> pd.Timestamp:
    return DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 11, day, hour, 30))


def _shv_game(shv_game_id=501, day=1, hour=18, opponent='HC Arbon 3', location='Uzwil bzu'):
    return ShvGame(shv_game_id=shv_game_id, timestamp=_ts(day, hour),
                   opponent=opponent, location=location, is_played=False)


def _bot_game(day=1, hour=18, opponent='HC Arbon 3', location='Uzwil bzu',
              shv_game_id=None, doc_id='game-1'):
    return Game(_ts(day, hour), location, opponent, shv_game_id, doc_id=doc_id)


def test_unknown_shv_game_is_added():
    sync_plan = GameSyncPlanner.plan([_shv_game()], [])

    assert len(sync_plan.to_add) == 1
    added = sync_plan.to_add[0]
    assert added.shv_game_id == 501
    assert added.opponent == 'HC Arbon 3'
    assert added.location == 'Uzwil bzu'
    assert added.timestamp == _ts(1)
    assert not sync_plan.to_update and not sync_plan.vanished


def test_linked_and_unchanged_game_yields_no_changes():
    sync_plan = GameSyncPlanner.plan([_shv_game()], [_bot_game(shv_game_id=501)])

    assert not sync_plan.has_changes()


def test_linked_game_with_new_date_and_venue_is_updated_in_place():
    bot_game = _bot_game(day=1, shv_game_id=501, doc_id='game-7')

    sync_plan = GameSyncPlanner.plan([_shv_game(day=8, location='Wil Lindenhof')], [bot_game])

    assert len(sync_plan.to_update) == 1
    update = sync_plan.to_update[0]
    assert update.game.doc_id == 'game-7'  # same row: attendance answers survive
    assert update.game.timestamp == _ts(8)
    assert update.game.location == 'Wil Lindenhof'
    assert update.old_timestamp == _ts(1)
    assert update.old_location == 'Uzwil bzu'
    assert not sync_plan.to_add


def test_unlinked_game_is_adopted_via_opponent_despite_spelling_differences():
    bot_game = _bot_game(opponent='  hc ARBON  3 ', location='somewhere', doc_id='manual-1')

    sync_plan = GameSyncPlanner.plan([_shv_game()], [bot_game])

    assert not sync_plan.to_add
    assert len(sync_plan.to_update) == 1
    update = sync_plan.to_update[0]
    assert update.game.doc_id == 'manual-1'
    assert update.game.shv_game_id == 501  # adoption always persists the link


def test_adoption_picks_the_candidate_closest_in_time():
    home_round = _bot_game(day=1, doc_id='home-round')
    away_round = _bot_game(day=20, doc_id='away-round')

    sync_plan = GameSyncPlanner.plan([_shv_game(day=19, location='elsewhere')],
                                     [home_round, away_round])

    assert [update.game.doc_id for update in sync_plan.to_update] == ['away-round']


def test_each_bot_game_adopts_at_most_one_shv_game():
    bot_game = _bot_game(day=1, doc_id='only-one')

    sync_plan = GameSyncPlanner.plan([_shv_game(shv_game_id=501, day=1),
                                      _shv_game(shv_game_id=502, day=20)], [bot_game])

    assert [update.game.doc_id for update in sync_plan.to_update] == ['only-one']
    assert [game.shv_game_id for game in sync_plan.to_add] == [502]


def test_linked_game_missing_from_feed_is_reported_vanished_not_deleted():
    linked = _bot_game(shv_game_id=999, doc_id='linked')
    manual = _bot_game(opponent='HC Other', doc_id='manual')

    sync_plan = GameSyncPlanner.plan([], [linked, manual])

    assert [game.doc_id for game in sync_plan.vanished] == ['linked']
    assert not sync_plan.to_add and not sync_plan.to_update
