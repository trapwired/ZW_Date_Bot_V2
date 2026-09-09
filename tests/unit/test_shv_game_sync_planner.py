"""Unit: the SHV sync diff - what is applied automatically, what becomes an admin
question, and how earlier answers (declined pairs, kept manual games) shape it."""
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


def _empty(sync_plan, *except_fields):
    for field in ('auto_updates', 'adopt_questions', 'new_games', 'vanished', 'manual_leftovers'):
        if field not in except_fields:
            assert getattr(sync_plan, field) == [], field


def test_unknown_shv_game_becomes_a_create_question():
    sync_plan = GameSyncPlanner.plan([_shv_game()], [])

    assert [game.shv_game_id for game in sync_plan.new_games] == [501]
    _empty(sync_plan, 'new_games')


def test_linked_and_unchanged_game_yields_nothing():
    sync_plan = GameSyncPlanner.plan([_shv_game()], [_bot_game(shv_game_id=501)])

    _empty(sync_plan)


def test_linked_game_with_new_date_and_venue_is_updated_automatically():
    bot_game = _bot_game(day=1, shv_game_id=501, doc_id='game-7')

    sync_plan = GameSyncPlanner.plan([_shv_game(day=8, location='Wil Lindenhof')], [bot_game])

    assert len(sync_plan.auto_updates) == 1
    update = sync_plan.auto_updates[0]
    assert update.game.doc_id == 'game-7'  # same row: attendance answers survive
    assert update.game.timestamp == _ts(8)
    assert update.game.location == 'Wil Lindenhof'
    assert update.old_timestamp == _ts(1)
    assert update.old_location == 'Uzwil bzu'
    _empty(sync_plan, 'auto_updates')


def test_unlinked_game_with_matching_opponent_is_adopted_automatically():
    bot_game = _bot_game(opponent='  hc ARBON  3 ', location='somewhere', doc_id='manual-1')

    sync_plan = GameSyncPlanner.plan([_shv_game()], [bot_game])

    assert len(sync_plan.auto_updates) == 1
    update = sync_plan.auto_updates[0]
    assert update.game.doc_id == 'manual-1'
    assert update.game.shv_game_id == 501  # adoption always persists the link
    _empty(sync_plan, 'auto_updates')


def test_manual_entry_is_adopted_by_its_own_round_despite_feed_order():
    # Found in live testing: the feed lists home/away rounds arbitrarily - the
    # February return round must not grab a manual 31.10 entry just because the
    # API happened to list it first.
    manual = _bot_game(day=1, doc_id='october-entry')
    return_round = ShvGame(shv_game_id=602, timestamp=_ts(1) + pd.Timedelta(days=98),
                           opponent='HC Arbon 3', location='Uzwil bzu', is_played=False)

    sync_plan = GameSyncPlanner.plan([return_round, _shv_game(shv_game_id=601, day=1)], [manual])

    assert [update.game.shv_game_id for update in sync_plan.auto_updates] == [601]
    assert [game.shv_game_id for game in sync_plan.new_games] == [602]


def test_opponent_adoption_never_reaches_across_to_the_other_round():
    # Only a far-away entry exists (the return round, pre-entered): the near feed
    # game must become a create question, not drag that entry months backwards.
    far_manual = _bot_game(day=1, doc_id='february-entry')
    near_feed_game = ShvGame(shv_game_id=601, timestamp=_ts(1) - pd.Timedelta(days=98),
                             opponent='HC Arbon 3', location='Uzwil bzu', is_played=False)

    sync_plan = GameSyncPlanner.plan([near_feed_game], [far_manual])

    assert [game.shv_game_id for game in sync_plan.new_games] == [601]
    assert [game.doc_id for game in sync_plan.manual_leftovers] == ['february-entry']


def test_opponent_adoption_picks_the_candidate_closest_in_time():
    home_round = _bot_game(day=1, doc_id='home-round')
    away_round = _bot_game(day=20, doc_id='away-round')

    sync_plan = GameSyncPlanner.plan([_shv_game(day=19, location='elsewhere')],
                                     [home_round, away_round])

    assert [update.game.doc_id for update in sync_plan.auto_updates] == ['away-round']
    assert [game.doc_id for game in sync_plan.manual_leftovers] == ['home-round']


def test_same_date_different_opponent_becomes_an_adopt_question():
    bot_game = _bot_game(opponent='Arbon', doc_id='manual-1')  # more than a spelling variant

    sync_plan = GameSyncPlanner.plan([_shv_game()], [bot_game])

    assert len(sync_plan.adopt_questions) == 1
    question = sync_plan.adopt_questions[0]
    assert question.bot_game.doc_id == 'manual-1'
    assert question.shv_game.shv_game_id == 501
    _empty(sync_plan, 'adopt_questions')


def test_declined_adopt_pair_is_not_asked_again_and_the_shv_game_becomes_new():
    bot_game = _bot_game(opponent='Arbon', doc_id='manual-1')

    sync_plan = GameSyncPlanner.plan([_shv_game()], [bot_game],
                                     declined_adopt_pairs={(501, 'manual-1')})

    assert [game.shv_game_id for game in sync_plan.new_games] == [501]
    assert [game.doc_id for game in sync_plan.manual_leftovers] == ['manual-1']
    _empty(sync_plan, 'new_games', 'manual_leftovers')


def test_kept_manual_game_stays_out_of_matching_and_questions():
    friendly = _bot_game(opponent='HC Arbon 3', doc_id='friendly')  # would match tier 2

    sync_plan = GameSyncPlanner.plan([_shv_game()], [friendly],
                                     kept_manual_doc_ids={'friendly'})

    assert [game.shv_game_id for game in sync_plan.new_games] == [501]
    _empty(sync_plan, 'new_games')


def test_each_bot_game_matches_at_most_one_shv_game():
    bot_game = _bot_game(day=1, doc_id='only-one')

    sync_plan = GameSyncPlanner.plan([_shv_game(shv_game_id=501, day=1),
                                      _shv_game(shv_game_id=502, day=20)], [bot_game])

    assert [update.game.doc_id for update in sync_plan.auto_updates] == ['only-one']
    assert [game.shv_game_id for game in sync_plan.new_games] == [502]


def test_linked_game_missing_from_feed_is_a_delete_question():
    linked = _bot_game(shv_game_id=999, doc_id='linked')

    sync_plan = GameSyncPlanner.plan([], [linked])

    assert [game.doc_id for game in sync_plan.vanished] == ['linked']
    _empty(sync_plan, 'vanished')


def test_unlinked_unmatched_game_is_a_manual_leftover_question():
    manual = _bot_game(opponent='HC Other', doc_id='manual')

    sync_plan = GameSyncPlanner.plan([], [manual])

    assert [game.doc_id for game in sync_plan.manual_leftovers] == ['manual']
    _empty(sync_plan, 'manual_leftovers')
