"""Feed rules (plan §6): which events a member's feed shows and how each is marked,
plus the drift guard between the per-event download and the feed."""
import pandas as pd
import pytest

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role

from domain.calendar.CalendarFeed import EVENT_DURATION, build_feed_entries
from domain.calendar.EventSummary import event_summary
from domain.calendar.Ics import event_uid
from domain.entities.Attendance import Attendance
from domain.entities.Game import Game
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training

from localization.LanguageContext import language_context

from Utils import PathUtils

TEAM = 'Züri West'
NO_ROW = None


def zurich(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz='Europe/Zurich')


def a_game(doc_id='game-1', start='2030-01-15 14:30', location='Home Arena') -> Game:
    return Game(zurich(start), location, 'rivals fc', doc_id=doc_id)


def a_training(doc_id='training-1', start='2030-01-14 19:00', location='Gym') -> Training:
    return Training(zurich(start), location, doc_id=doc_id)


def a_timekeeping(doc_id='timekeeping-1', start='2030-01-16 10:00') -> TimekeepingEvent:
    return TimekeepingEvent(zurich(start), 'Hall', 2, doc_id=doc_id)


def attendances_for(event, state) -> dict[str, Attendance]:
    if state is NO_ROW:
        return {}
    return {event.doc_id: Attendance('user-1', event.doc_id, state)}


def only_entry(entries):
    [single] = entries
    return single


@pytest.mark.parametrize('state, prefix, status, answer', [
    (AttendanceState.YES, '✅ ', 'CONFIRMED', '✅ Yes'),
    (AttendanceState.UNSURE, '❓ ', 'TENTATIVE', '❓ Unsure'),
    (NO_ROW, '❓ ', 'TENTATIVE', '❓ Unsure'),
])
def test_member_who_can_answer_sees_own_answer(state, prefix, status, answer):
    game = a_game()
    feed_entry = only_entry(build_feed_entries({Event.GAME: [game]}, attendances_for(game, state),
                                               role=Role.PLAYER, team_name=TEAM))
    assert feed_entry.summary == prefix + 'Handball Game Züri West (rivals fc)'
    assert feed_entry.status == status
    assert feed_entry.description == f'Your answer: {answer}'


def test_declined_event_is_left_out():
    game = a_game()
    entries = build_feed_entries({Event.GAME: [game]}, attendances_for(game, AttendanceState.NO),
                                 role=Role.PLAYER, team_name=TEAM)
    assert entries == []


@pytest.mark.parametrize('state', [AttendanceState.YES, AttendanceState.UNSURE, AttendanceState.NO, NO_ROW])
def test_member_who_cannot_answer_sees_every_event_unmarked(state):
    game = a_game()
    feed_entry = only_entry(build_feed_entries({Event.GAME: [game]}, attendances_for(game, state),
                                               role=Role.SPECTATOR, team_name=TEAM))
    assert feed_entry.summary == 'Handball Game Züri West (rivals fc)'
    assert feed_entry.status == 'CONFIRMED'
    assert feed_entry.description is None


def test_entry_carries_uid_times_and_location_of_its_event():
    game = a_game()
    feed_entry = only_entry(build_feed_entries({Event.GAME: [game]}, {}, role=Role.PLAYER, team_name=TEAM))
    assert feed_entry.uid == event_uid('game-1')
    assert feed_entry.start == zurich('2030-01-15 14:30')
    assert feed_entry.start.tzinfo is not None
    assert feed_entry.end == feed_entry.start + EVENT_DURATION
    assert feed_entry.location == 'Home Arena'


def test_empty_location_becomes_none():
    feed_entry = only_entry(build_feed_entries({Event.TRAINING: [a_training(location='')]}, {},
                                               role=Role.PLAYER, team_name=TEAM))
    assert feed_entry.location is None


def test_titles_per_event_type_come_from_the_shared_summary():
    events_by_type = {Event.GAME: [a_game()], Event.TRAINING: [a_training()], Event.TIMEKEEPING: [a_timekeeping()]}
    summaries = {entry.uid: entry.summary
                 for entry in build_feed_entries(events_by_type, {}, role=Role.PLAYER, team_name=TEAM)}
    assert summaries == {
        event_uid('game-1'): '❓ Handball Game Züri West (rivals fc)',
        event_uid('training-1'): '❓ Handball Training Züri West',
        event_uid('timekeeping-1'): '❓ Handball Timekeeping Züri West',
    }


def test_spectator_never_gets_timekeeping_even_when_handed_it():
    events_by_type = {Event.GAME: [a_game()], Event.TIMEKEEPING: [a_timekeeping()]}
    entries = build_feed_entries(events_by_type, {}, role=Role.SPECTATOR, team_name=TEAM)
    assert [entry.uid for entry in entries] == [event_uid('game-1')]


def test_retired_member_is_marked_like_a_player():
    game = a_game()
    feed_entry = only_entry(build_feed_entries({Event.GAME: [game]}, attendances_for(game, AttendanceState.YES),
                                               role=Role.RETIRED, team_name=TEAM))
    assert feed_entry.summary.startswith('✅ ')


def test_entries_are_sorted_by_start_then_uid_across_types():
    events_by_type = {
        Event.GAME: [a_game('game-b', start='2030-01-20 14:00'), a_game('game-a', start='2030-01-20 14:00')],
        Event.TRAINING: [a_training('training-1', start='2030-01-14 19:00')],
        Event.TIMEKEEPING: [a_timekeeping('timekeeping-1', start='2030-01-02 10:00')],
    }
    entries = build_feed_entries(events_by_type, {}, role=Role.PLAYER, team_name=TEAM)
    assert [entry.uid for entry in entries] == [event_uid(doc_id) for doc_id in
                                                ('timekeeping-1', 'training-1', 'game-a', 'game-b')]


def test_texts_follow_the_ambient_language():
    game = a_game()
    with language_context('de'):
        feed_entry = only_entry(build_feed_entries({Event.GAME: [game]}, attendances_for(game, AttendanceState.YES),
                                                   role=Role.PLAYER, team_name=TEAM))
    assert feed_entry.summary == '✅ Handball Spiel Züri West (rivals fc)'
    assert feed_entry.description == 'Deine Antwort: ✅ Ja'


def test_per_event_download_and_feed_share_title_and_uid(services, game, tmp_path, monkeypatch):
    monkeypatch.setattr(PathUtils, 'get_ics_files_path', lambda: str(tmp_path))
    team_name = services['team_service'].current_team().name

    ics_path = services['ics_service'].get_ics(Event.GAME, game.doc_id)

    with open(ics_path, encoding='utf-8') as ics_file:
        lines = ics_file.read().splitlines()
    assert f'SUMMARY:{event_summary(Event.GAME, game, team_name)}' in lines
    assert f'UID:{event_uid(game.doc_id)}' in lines
