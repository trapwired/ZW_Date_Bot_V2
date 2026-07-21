"""The seam's semantics, asserted identically against both backends (see conftest).

Each block covers one contract from data/Repository.py: row duck type, add()
returning the id, ObjectNotFoundException on missing documents - plus the
method-level behaviors DataAccess relies on (count guards, self-heal, upsert,
tenancy scoping).
"""
from datetime import datetime, timedelta

import pytest

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role
from Enums.Table import Table
from Enums.UserState import UserState

from data.TenantContext import set_current_team, reset_current_team

from domain.entities.Attendance import Attendance
from domain.entities.Game import Game
from domain.entities.Settings import Settings
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.TempData import TempData
from domain.entities.UsersToState import UsersToState

from Utils.CustomExceptions import ObjectNotFoundException, MoreThanOneObjectFoundException, \
    NoTempDataFoundException


def _seed_user(repository, telegram_id=777):
    user_doc_id = repository.add(TelegramUser(telegram_id, 'Contract', 'Tester'), Table.USERS_TABLE)
    return repository.get_user(user_doc_id)


def _seed_state(repository, user, role=Role.PLAYER, is_admin=False, team=True):
    from data.TenantContext import current_team_id
    uts = UsersToState(user.doc_id, UserState.DEFAULT, role=role, is_admin=is_admin,
                       team_id=current_team_id() if team else None)
    doc_id = repository.add(uts, Table.USERS_TO_STATE_TABLE)
    return uts.add_document_id(doc_id)


# --- core contracts ---------------------------------------------------------

def test_add_returns_the_new_id_and_get_document_round_trips(repository):
    doc_id = repository.add(Game(datetime(2030, 3, 1, 20, 15), 'Saalsporthalle', 'HC Test'),
                            Table.GAMES_TABLE)
    assert isinstance(doc_id, str) and doc_id

    row = repository.get_document(doc_id, Table.GAMES_TABLE)
    assert row.id == doc_id
    assert row.to_dict()['location'] == 'Saalsporthalle'
    assert row.to_dict()['opponent'] == 'HC Test'


def test_get_document_missing_raises_object_not_found(repository):
    with pytest.raises(ObjectNotFoundException):
        repository.get_document('no-such-id', Table.GAMES_TABLE)


def test_update_missing_document_raises_object_not_found(repository):
    game = Game(datetime(2030, 3, 1, 20, 15), 'Halle', 'X')
    game.add_document_id('no-such-id')
    with pytest.raises(ObjectNotFoundException):
        repository.update(game, Table.GAMES_TABLE)


def test_update_overwrites_fields(repository):
    doc_id = repository.add(Game(datetime(2030, 3, 1, 20, 15), 'Old', 'X'), Table.GAMES_TABLE)
    game = repository.get_game(doc_id)
    game.location = 'New'
    repository.update(game, Table.GAMES_TABLE)
    assert repository.get_game(doc_id).location == 'New'


# --- users + state ----------------------------------------------------------

def test_get_user_by_telegram_id_and_missing_raises(repository):
    user = _seed_user(repository, telegram_id=4242)
    assert repository.get_user(4242).doc_id == user.doc_id
    with pytest.raises(ObjectNotFoundException):
        repository.get_user(999999)


def test_get_user_state_roundtrip_and_corruption_guard(repository):
    user = _seed_user(repository)
    with pytest.raises(ObjectNotFoundException):
        repository.get_user_state(user)
    _seed_state(repository, user)
    assert repository.get_user_state(user).user_id == user.doc_id
    _seed_state(repository, user)  # duplicate = corruption, never silently picked
    with pytest.raises(MoreThanOneObjectFoundException):
        repository.get_user_state(user)


def test_update_user_state_via_user_id_persists_state_only(repository):
    user = _seed_user(repository)
    _seed_state(repository, user)
    detached = UsersToState(user.doc_id, UserState.REJECTED)
    repository.update_user_state_via_user_id(detached)
    assert repository.get_user_state(user).state == UserState.REJECTED


def test_roster_queries_filter_by_role_admin_flag_and_team(repository):
    player = _seed_state(repository, _seed_user(repository, 1))
    retired_admin = _seed_state(repository, _seed_user(repository, 2), role=Role.RETIRED, is_admin=True)
    _seed_state(repository, _seed_user(repository, 3), role=Role.PLAYER, team=False)  # other/no team

    active_ids = {row.to_dict()['userId'] for row in repository.get_all_active_players_to_state()}
    assert active_ids == {player.user_id}

    admin_ids = {row.to_dict()['userId'] for row in repository.get_admins_to_state()}
    assert admin_ids == {retired_admin.user_id}

    retired_ids = {row.to_dict()['userId'] for row in repository.get_users_to_state_by_role(Role.RETIRED)}
    assert retired_ids == {retired_admin.user_id}


# --- events + attendance ----------------------------------------------------

def test_future_events_excludes_past(repository):
    repository.add(Game(datetime.now() - timedelta(days=1), 'past', 'X'), Table.GAMES_TABLE)
    future_id = repository.add(Game(datetime.now() + timedelta(days=1), 'future', 'Y'), Table.GAMES_TABLE)
    rows = repository.get_future_events(Table.GAMES_TABLE)
    assert [row.id for row in rows] == [future_id]


def test_attendance_isolated_per_event_type(repository):
    user = _seed_user(repository)
    game_att = Attendance(user.doc_id, 'event-1', AttendanceState.YES)
    repository.add(game_att, Table.GAME_ATTENDANCE_TABLE)
    training_att = Attendance(user.doc_id, 'event-1', AttendanceState.NO)
    repository.add(training_att, Table.TRAINING_ATTENDANCE_TABLE)

    # Same event id, different event types: the one-table backend must keep them apart.
    game_rows = repository.get_attendance_list('event-1', Table.GAME_ATTENDANCE_TABLE)
    assert [AttendanceState(row.to_dict()['state']) for row in game_rows] == [AttendanceState.YES]

    found = repository.get_attendance(user, 'event-1', Table.TRAINING_ATTENDANCE_TABLE)
    assert found.state == AttendanceState.NO

    assert repository.get_event_attendance_doc_id(game_att, Table.GAME_ATTENDANCE_TABLE) is not None
    ghost = Attendance(user.doc_id, 'other-event', AttendanceState.YES)
    assert repository.get_event_attendance_doc_id(ghost, Table.GAME_ATTENDANCE_TABLE) is None


def test_delete_and_reset_event_attendances(repository):
    user = _seed_user(repository)
    repository.add(Attendance(user.doc_id, 'ev-1', AttendanceState.YES), Table.GAME_ATTENDANCE_TABLE)
    repository.add(Attendance(user.doc_id, 'ev-2', AttendanceState.YES), Table.GAME_ATTENDANCE_TABLE)

    repository.reset_all_player_event_attendance('ev-1', Table.GAME_ATTENDANCE_TABLE)
    reset_row = repository.get_attendance(user, 'ev-1', Table.GAME_ATTENDANCE_TABLE)
    assert AttendanceState(reset_row.state) == AttendanceState.UNSURE

    repository.delete_event_attendances(Event.GAME, 'ev-2')
    with pytest.raises(ObjectNotFoundException):
        repository.get_attendance(user, 'ev-2', Table.GAME_ATTENDANCE_TABLE)


def test_all_event_attendances_batches_and_empty_input(repository):
    user = _seed_user(repository)
    for n in range(35):  # crosses Firestore's 30-value 'in' batch limit
        repository.add(Attendance(user.doc_id, f'ev-{n}', AttendanceState.YES),
                       Table.GAME_ATTENDANCE_TABLE)
    ids = [f'ev-{n}' for n in range(35)]
    assert len(repository.get_all_event_attendances(Event.GAME, ids)) == 35
    assert repository.get_all_event_attendances(Event.GAME, []) == []


# --- player metric ----------------------------------------------------------

def test_player_metric_created_once_and_self_heals_duplicates(repository):
    user = _seed_user(repository)
    metric = repository.get_player_metric(user)
    assert metric.doc_id is not None
    again = repository.get_player_metric(user)
    assert again.doc_id == metric.doc_id  # found, not re-created

    repository.add(again, Table.PLAYER_METRIC)  # inject a duplicate
    healed = repository.get_player_metric(user)
    assert healed.doc_id is not None
    assert len(repository.get_all_player_metrics()) == 1  # collapsed back to one


# --- temp data, settings, teams --------------------------------------------

def test_temp_data_lookup_and_delete(repository):
    with pytest.raises(NoTempDataFoundException):
        repository.get_temp_data('nobody')
    temp = TempData('user-doc-1', Event.GAME, None, None, None, 5, 71)
    temp.add_document_id(repository.add(temp, Table.TEMP_DATA_TABLE))
    assert repository.get_temp_data('user-doc-1').chat_id == 5
    repository.delete_temp_data(temp)
    with pytest.raises(NoTempDataFoundException):
        repository.get_temp_data('user-doc-1')


def test_settings_upsert_roundtrip(repository):
    assert repository.get_settings() is None
    repository.set_settings(Settings('https://one.example'))
    repository.set_settings(Settings('https://two.example'))
    assert repository.get_settings().website == 'https://two.example'


def test_team_roundtrip_arrays_and_delete_team_purges_scoped_rows(repository):
    from data.TenantContext import current_team_id
    team_id = current_team_id()
    team = repository.get_team(team_id)
    assert team.name == 'Contract FC'

    team.trainers_games = [1, 2]
    team.invite_tokens = ['tok-a']
    repository.update(team, Table.TEAMS_TABLE)
    assert repository.get_team(team_id).trainers_games == [1, 2]

    repository.add(Game(datetime(2030, 5, 1), 'x', 'y'), Table.GAMES_TABLE)
    assert repository.has_any_docs(Table.GAMES_TABLE)
    repository.delete_team(team_id)
    assert not repository.has_any_docs(Table.GAMES_TABLE)
    assert all(t.doc_id != team_id for t in repository.get_all_teams())


# --- tenancy ----------------------------------------------------------------

def test_scoped_tables_are_isolated_between_teams(repository):
    repository.add(Game(datetime(2030, 4, 1), 'a-halle', 'X'), Table.GAMES_TABLE)

    other_team = repository.add(Team('Other FC', group_chat_id=-200456, spectator_password='other-pass'),
                                Table.TEAMS_TABLE)
    token = set_current_team(other_team)
    try:
        assert repository.get_future_events(Table.GAMES_TABLE) == []
        assert not repository.has_any_docs(Table.GAMES_TABLE)
    finally:
        reset_current_team(token)
