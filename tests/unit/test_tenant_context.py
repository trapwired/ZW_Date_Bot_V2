"""Unit: pins the tenancy seam (ADR 0001).

Two guarantees the whole multi-tenant design rests on:
- Fail-closed: touching a team-scoped collection with no team resolved raises rather
  than reading across tenants.
- Structural isolation: each team's data lives under its own subcollection, so one
  team never sees another's events - even for identical queries.
Global tables (identity + the team registry) stay reachable without a context.
"""
import pytest

from data.TenantContext import (set_current_team, reset_current_team, team_context,
                                 MissingTenantContextError)
from data.FirebaseRepository import GLOBAL_TABLES, TEAM_SCOPED_TABLES

from Enums.Table import Table
from Enums.Role import Role
from Enums.UserState import UserState

from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState
from domain.entities.Team import Team
from domain.entities.Game import Game
from domain.EventDateTimeParser import parse

from tests.helpers import seed_user


def _game(day: str) -> Game:
    return Game(parse(day).value, "home arena", "rivals fc")


def test_team_scoped_read_without_context_fails_closed(data_access):
    # The fixture set a context; drop it to prove team-scoped reads fail closed.
    token = set_current_team(None)
    try:
        with pytest.raises(MissingTenantContextError):
            data_access.get_ordered_games()
    finally:
        reset_current_team(token)


def test_global_tables_need_no_context(data_access):
    token = set_current_team(None)
    try:
        data_access.add(TelegramUser(555, "Global", "User"))
        assert data_access.get_user(555) is not None
    finally:
        reset_current_team(token)


def test_two_teams_are_fully_isolated(data_access):
    other = data_access.add(Team('Other', group_chat_id=999))

    # Default context (set by the fixture): one game lives here.
    default_game = data_access.add(_game("24.12.2030 18:30"))
    assert len(data_access.get_ordered_games()) == 1

    with team_context(other.doc_id):
        assert data_access.get_ordered_games() == []
        other_game = data_access.add(_game("25.12.2030 18:30"))
        assert len(data_access.get_ordered_games()) == 1

    # Back in the default context: the other team's game is invisible.
    default_games = data_access.get_ordered_games()
    assert len(default_games) == 1
    assert default_games[0].doc_id == default_game.doc_id
    assert default_games[0].doc_id != other_game.doc_id


def test_every_table_is_classified():
    assert GLOBAL_TABLES | TEAM_SCOPED_TABLES == set(Table)
    assert not (GLOBAL_TABLES & TEAM_SCOPED_TABLES)


def test_users_to_state_team_id_roundtrip(data_access):
    seed_user(data_access, 4242, Role.PLAYER, UserState.DEFAULT, team_id="team-xyz")

    reloaded = data_access.get_user_state(4242)
    assert reloaded.team_id == "team-xyz"

    # A legacy state doc predating tenancy has no 'teamId' - it must load as None.
    legacy = UsersToState.from_dict('d1', {
        'userId': 'u1',
        'state': int(UserState.DEFAULT),
        'additionalInformation': '',
        'role': int(Role.PLAYER),
    })
    assert legacy.team_id is None
