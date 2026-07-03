"""Unit: Team.trainer_chat_ids - the per-team trainer routing rule."""
import pytest

from Enums.Event import Event
from domain.entities.Team import Team

GROUP = -100555


def _team(**kwargs):
    return Team('Berg', group_chat_id=GROUP, **kwargs)


def test_training_goes_to_training_trainers():
    team = _team(trainers_games=[1], trainers_training=[2, 3])
    assert team.trainer_chat_ids(Event.TRAINING) == [2, 3]


@pytest.mark.parametrize('event_type', [Event.GAME, Event.TIMEKEEPING])
def test_games_and_timekeeping_go_to_game_trainers(event_type):
    team = _team(trainers_games=[1], trainers_training=[2, 3])
    assert team.trainer_chat_ids(event_type) == [1]


@pytest.mark.parametrize('event_type', list(Event))
def test_team_without_trainers_falls_back_to_its_group_chat(event_type):
    assert _team().trainer_chat_ids(event_type) == [GROUP]


def test_toggle_trainer_adds_then_removes():
    team = _team()
    team.toggle_trainer(Event.GAME, 7)
    assert team.trainers_games == [7] and team.trainers_training == []
    team.toggle_trainer(Event.GAME, 7)
    assert team.trainers_games == []


def test_trainer_lists_coerce_and_dedupe_hand_edited_ids():
    team = Team('Berg', group_chat_id=GROUP, trainers_games=['911000001', 911000001, 7])
    assert team.trainers_games == [911000001, 7]


def test_toggle_trainer_via_timekeeping_edits_the_games_list():
    team = _team()
    team.toggle_trainer(Event.TIMEKEEPING, 7)
    assert team.trainers_games == [7]
