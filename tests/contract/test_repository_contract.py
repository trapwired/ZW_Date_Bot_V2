"""The seam's semantics, asserted identically against both backends (see conftest).

Each block covers one contract from data/Repository.py: row duck type, add()
returning the id, ObjectNotFoundException on missing documents - plus the
method-level behaviors DataAccess relies on (count guards, self-heal, upsert,
tenancy scoping).
"""
from datetime import datetime, timedelta

import pandas as pd
import pytest

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role
from Enums.Table import Table
from Enums.UserState import UserState

from data.TenantContext import set_current_team, reset_current_team

from domain.entities.Attendance import Attendance
from domain.entities.CalendarToken import CalendarToken
from domain.entities.Game import Game
from domain.entities.Settings import Settings
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.TempData import TempData
from domain.entities.Training import Training
from domain.entities.UsersToState import UsersToState

from Utils import DateTimeUtils
from Utils.CustomExceptions import ObjectNotFoundException, MoreThanOneObjectFoundException, \
    NoTempDataFoundException


_CREATED_AT = DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 6, 1, 12, 0))


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


def test_events_since_includes_the_boundary_and_excludes_earlier_events(repository):
    since = DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 6, 1, 18, 0))
    repository.add(Game(since - timedelta(minutes=1), 'before', 'X'), Table.GAMES_TABLE)
    on_boundary = repository.add(Game(since, 'boundary', 'Y'), Table.GAMES_TABLE)
    after = repository.add(Game(since + timedelta(days=30), 'after', 'Z'), Table.GAMES_TABLE)
    repository.add(Training(since + timedelta(hours=1), 'other table'), Table.TRAININGS_TABLE)

    assert {row.id for row in repository.get_events_since(Table.GAMES_TABLE, since)} == {on_boundary, after}
    # The same instant written as a UTC wall clock must select the same events.
    in_utc = since.tz_convert('UTC')
    assert {row.id for row in repository.get_events_since(Table.GAMES_TABLE, in_utc)} == {on_boundary, after}
    assert len(repository.get_events_since(Table.TRAININGS_TABLE, since)) == 1


def test_events_since_is_scoped_to_the_current_team(repository):
    since = DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 6, 1, 18, 0))
    repository.add(Game(since, 'ours', 'X'), Table.GAMES_TABLE)

    other_team = repository.add(Team('Other FC', group_chat_id=-200789, spectator_password='other-pass'),
                                Table.TEAMS_TABLE)
    token = set_current_team(other_team)
    try:
        assert repository.get_events_since(Table.GAMES_TABLE, since) == []
    finally:
        reset_current_team(token)


def test_data_access_events_since_returns_sorted_entities_and_rejects_naive_bounds(repository, api_config):
    from data.DataAccess import DataAccess
    data_access = DataAccess(api_config, repository=repository)
    since = DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 6, 1, 18, 0))
    later = repository.add(Game(since + timedelta(days=2), 'later', 'B'), Table.GAMES_TABLE)
    sooner = repository.add(Game(since, 'sooner', 'A'), Table.GAMES_TABLE)

    games = data_access.get_events_since(Event.GAME, since)

    assert [game.doc_id for game in games] == [sooner, later]
    assert all(isinstance(game, Game) for game in games)
    with pytest.raises(ValueError):
        data_access.get_events_since(Event.GAME, datetime(2030, 6, 1, 18, 0))


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
    for n in range(35):  # large id list (crossed the Firestore-era 30-value batch limit)
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


def test_delete_user_data_purges_every_trace_of_one_user_only(repository):
    user = _seed_user(repository, telegram_id=801)
    _seed_state(repository, user)
    other = _seed_user(repository, telegram_id=802)
    _seed_state(repository, other)

    repository.add(Attendance(user.doc_id, 'ev-1', AttendanceState.YES), Table.GAME_ATTENDANCE_TABLE)
    repository.add(Attendance(user.doc_id, 'ev-2', AttendanceState.NO), Table.TRAINING_ATTENDANCE_TABLE)
    repository.add(Attendance(other.doc_id, 'ev-1', AttendanceState.YES), Table.GAME_ATTENDANCE_TABLE)
    repository.get_player_metric(user)  # self-creates the metric row
    draft = TempData(user.doc_id, Event.GAME, None, None, None, 5, 71)
    draft.add_document_id(repository.add(draft, Table.TEMP_DATA_TABLE))
    repository.replace_calendar_token(user.doc_id, 'hash-gone', _CREATED_AT)
    repository.replace_calendar_token(other.doc_id, 'hash-stays', _CREATED_AT)

    repository.delete_user_data(user.doc_id)

    with pytest.raises(ObjectNotFoundException):
        repository.get_user(user.doc_id)
    with pytest.raises(ObjectNotFoundException):
        repository.get_user_state(user)
    assert repository.get_all_user_event_attendance(user, Event.GAME) == []
    assert repository.get_all_user_event_attendance(user, Event.TRAINING) == []
    assert len(repository.get_all_player_metrics()) == 0
    with pytest.raises(NoTempDataFoundException):
        repository.get_temp_data(user.doc_id)

    assert repository.get_calendar_token_by_user(user.doc_id) is None
    assert repository.get_calendar_token_by_hash('hash-gone') is None

    # The other user's rows are untouched.
    assert repository.get_user_state(other) is not None
    assert len(repository.get_all_user_event_attendance(other, Event.GAME)) == 1
    assert repository.get_calendar_token_by_hash('hash-stays') is not None


# --- calendar tokens --------------------------------------------------------

def test_replacing_a_calendar_token_retires_the_previous_one(repository):
    user = _seed_user(repository)
    repository.replace_calendar_token(user.doc_id, 'hash-old', _CREATED_AT)
    repository.replace_calendar_token(user.doc_id, 'hash-new', _CREATED_AT + timedelta(hours=1))

    assert repository.get_calendar_token_by_hash('hash-old') is None
    current = repository.get_calendar_token_by_user(user.doc_id)
    token = CalendarToken.from_dict(current.id, current.to_dict())
    assert token.token_hash == 'hash-new'
    assert token.created_at == _CREATED_AT + timedelta(hours=1)  # same instant, tz-independent
    assert repository.get_calendar_token_by_hash('hash-new').id == current.id


def test_calendar_token_lookup_by_hash_and_by_user_keeps_users_apart(repository):
    alice = _seed_user(repository, telegram_id=901)
    bob = _seed_user(repository, telegram_id=902)
    repository.replace_calendar_token(alice.doc_id, 'hash-alice', _CREATED_AT)
    repository.replace_calendar_token(bob.doc_id, 'hash-bob', _CREATED_AT)

    by_hash = repository.get_calendar_token_by_hash('hash-alice')
    assert by_hash.to_dict()['userId'] == alice.doc_id
    assert by_hash.to_dict()['lastUsedAt'] is None
    assert repository.get_calendar_token_by_user(bob.doc_id).to_dict()['tokenHash'] == 'hash-bob'

    assert repository.get_calendar_token_by_hash('no-such-hash') is None
    assert repository.get_calendar_token_by_user('no-such-user') is None


def test_touching_a_calendar_token_stamps_last_used_and_replacing_resets_it(repository):
    user = _seed_user(repository)
    repository.replace_calendar_token(user.doc_id, 'hash-1', _CREATED_AT)
    used_at = _CREATED_AT + timedelta(days=2)

    repository.touch_calendar_token('hash-1', used_at)
    stamped = CalendarToken.from_dict('x', repository.get_calendar_token_by_hash('hash-1').to_dict())
    assert stamped.last_used_at == used_at
    assert stamped.created_at == _CREATED_AT  # touching never moves the creation time

    repository.touch_calendar_token('no-such-hash', used_at)  # lost a race with a rotation: no-op

    repository.replace_calendar_token(user.doc_id, 'hash-2', _CREATED_AT)
    assert repository.get_calendar_token_by_user(user.doc_id).to_dict()['lastUsedAt'] is None


def test_deleting_a_calendar_token_by_user_leaves_other_users_alone(repository):
    alice = _seed_user(repository, telegram_id=903)
    bob = _seed_user(repository, telegram_id=904)
    repository.replace_calendar_token(alice.doc_id, 'hash-alice', _CREATED_AT)
    repository.replace_calendar_token(bob.doc_id, 'hash-bob', _CREATED_AT)

    repository.delete_calendar_token(alice.doc_id)
    repository.delete_calendar_token(alice.doc_id)  # already gone: no-op

    assert repository.get_calendar_token_by_user(alice.doc_id) is None
    assert repository.get_calendar_token_by_hash('hash-alice') is None
    assert repository.get_calendar_token_by_hash('hash-bob') is not None


def test_calendar_tokens_need_no_tenant_context(repository):
    # The feed server resolves a token before it knows which team the user belongs to.
    tenant = set_current_team(None)
    try:
        repository.replace_calendar_token('user-1', 'hash-1', _CREATED_AT)
        assert repository.get_calendar_token_by_hash('hash-1') is not None
        repository.touch_calendar_token('hash-1', _CREATED_AT)
        assert repository.get_calendar_token_by_user('user-1') is not None
        repository.delete_calendar_token('user-1')
        assert repository.get_calendar_token_by_hash('hash-1') is None
    finally:
        reset_current_team(tenant)


def test_data_access_calendar_token_wrappers_return_entities(repository, api_config):
    from data.DataAccess import DataAccess
    data_access = DataAccess(api_config, repository=repository)
    user = _seed_user(repository)
    assert data_access.get_calendar_token(user.doc_id) is None
    assert data_access.find_calendar_token_by_hash('hash-1') is None

    data_access.replace_calendar_token(user.doc_id, 'hash-1', _CREATED_AT)
    data_access.touch_calendar_token('hash-1', _CREATED_AT + timedelta(hours=3))

    token = data_access.get_calendar_token(user.doc_id)
    assert (token.token_hash, token.user_id, token.created_at) == ('hash-1', user.doc_id, _CREATED_AT)
    assert token.last_used_at == _CREATED_AT + timedelta(hours=3)
    assert data_access.find_calendar_token_by_hash('hash-1').doc_id == token.doc_id

    data_access.delete_calendar_token(user.doc_id)
    assert data_access.get_calendar_token(user.doc_id) is None


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
    repository.set_settings(Settings('https://two.example', shv_sync_disabled=True))
    settings = repository.get_settings()
    assert settings.website == 'https://two.example'
    assert settings.shv_sync_disabled is True


def test_shv_sync_decision_roundtrip_update_and_delete(repository):
    import pandas as pd
    from domain.entities.ShvSyncDecision import ShvSyncDecision
    from Enums.ShvSync import ShvDecisionKind, ShvDecisionStatus
    from Utils import DateTimeUtils

    asked_at = DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 11, 1, 6, 30))
    decision = ShvSyncDecision('tok_abc123', ShvDecisionKind.CREATE, ShvDecisionStatus.PENDING,
                               shv_game_id=509764, asked_at=asked_at)
    doc_id = repository.add(decision, Table.SHV_SYNC_DECISIONS_TABLE)

    rows = repository.get_shv_sync_decisions()
    assert len(rows) == 1
    loaded = ShvSyncDecision.from_dict(rows[0].id, rows[0].to_dict())
    assert (loaded.token, loaded.kind, loaded.status) == \
        ('tok_abc123', ShvDecisionKind.CREATE, ShvDecisionStatus.PENDING)
    assert loaded.shv_game_id == 509764
    assert loaded.game_doc_id is None and loaded.reason is None
    assert loaded.asked_at == asked_at  # same instant, tz-representation-independent

    loaded.status = ShvDecisionStatus.DECLINED
    loaded.reason = 'friendly game'
    repository.update(loaded, Table.SHV_SYNC_DECISIONS_TABLE)
    reloaded = ShvSyncDecision.from_dict(doc_id, repository.get_shv_sync_decisions()[0].to_dict())
    assert reloaded.status == ShvDecisionStatus.DECLINED
    assert reloaded.reason == 'friendly game'

    repository.delete_shv_sync_decision(doc_id)
    assert repository.get_shv_sync_decisions() == []


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
