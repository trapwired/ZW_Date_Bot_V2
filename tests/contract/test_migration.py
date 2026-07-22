"""Stage B3: the Firestore→Postgres copy preserves ids, fields, tenancy and the
attendance discriminator - and is idempotent (the cutover reruns it for the
final delta). Runs against the fake Firestore + a real Postgres (skips without
one, like the rest of tests/contract)."""
from datetime import datetime

import pytest

from data.Tables import Tables

from Enums.AttendanceState import AttendanceState
from Enums.Role import Role
from Enums.Table import Table
from Enums.UserState import UserState

from domain.entities.Attendance import Attendance
from domain.entities.Game import Game
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState

from scripts.migrate_firestore_to_postgres import migrate, upsert  # noqa: F401

from tests.contract.conftest import _firestore_repository, _postgres_repository, _truncate_all


@pytest.fixture
def stores(monkeypatch, api_config):
    firebase = _firestore_repository(monkeypatch, api_config)
    postgres = _postgres_repository()
    _truncate_all(postgres)
    yield firebase, postgres, firebase.db, Tables(api_config)
    postgres.pool.close()


def _populate(firebase):
    from data.TenantContext import set_current_team, reset_current_team
    team_id = firebase.add(Team('Mig FC', group_chat_id=-1, spectator_password='mig-pass-1'),
                           Table.TEAMS_TABLE)
    token = set_current_team(team_id)
    try:
        user_doc = firebase.add(TelegramUser(42, 'Mig', 'User'), Table.USERS_TABLE)
        firebase.add(UsersToState(user_doc, UserState.DEFAULT, role=Role.RETIRED, is_admin=True,
                                  team_id=team_id), Table.USERS_TO_STATE_TABLE)
        game_id = firebase.add(Game(datetime(2030, 9, 1, 20, 0), 'Halle', 'HC Mig'), Table.GAMES_TABLE)
        firebase.add(Attendance(user_doc, game_id, AttendanceState.YES), Table.GAME_ATTENDANCE_TABLE)
        firebase.add(Attendance(user_doc, game_id, AttendanceState.NO), Table.TRAINING_ATTENDANCE_TABLE)
    finally:
        reset_current_team(token)
    return team_id, user_doc, game_id


def test_migration_preserves_ids_fields_tenancy_and_discriminator(stores):
    firebase, postgres, db, tables = stores
    team_id, user_doc, game_id = _populate(firebase)

    migrate(db, tables, postgres)

    game = postgres._execute('SELECT team_id, location, opponent FROM games WHERE id = %s',
                             (game_id,)).fetchone()
    assert game == (team_id, 'Halle', 'HC Mig')

    uts = postgres._execute('SELECT user_id, role, is_admin, team_id FROM users_to_state').fetchone()
    assert uts == (user_doc, int(Role.RETIRED), True, team_id)

    states = postgres._execute(
        'SELECT event_type, state FROM attendance ORDER BY event_type').fetchall()
    assert states == [(0, int(AttendanceState.YES)), (1, int(AttendanceState.NO))]


def test_migration_is_idempotent(stores):
    firebase, postgres, db, tables = stores
    _populate(firebase)

    migrate(db, tables, postgres)
    first = postgres._execute('SELECT count(*) FROM attendance').fetchone()[0]
    migrate(db, tables, postgres)  # rerun = same state, no duplicates
    assert postgres._execute('SELECT count(*) FROM attendance').fetchone()[0] == first
