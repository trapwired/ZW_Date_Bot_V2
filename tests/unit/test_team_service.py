"""Unit: TeamService - the team registry and per-team lookups (multi-tenancy PR 2/3).

The fixture registers a default 'Züri West' team and sets it as the ambient tenant
context (see tests/conftest.py). These tests pin the registry behaviour: group-chat
uniqueness, spectator-password lookup/uniqueness, and that our own writes stay
consistent with the write-through cache.
"""
import pytest

from framework.Services.TeamService import TeamService
from Utils.CustomExceptions import (GroupChatAlreadyRegisteredException,
                                     SpectatorPasswordAlreadyTakenException)


def test_register_team_creates_and_is_findable_by_group_chat(data_access):
    service = TeamService(data_access)

    team = service.register_team('Other', group_chat_id=999)

    assert team.doc_id is not None
    assert service.find_team_by_group_chat(999).doc_id == team.doc_id


def test_register_same_group_chat_twice_raises(data_access):
    service = TeamService(data_access)
    service.register_team('Other', group_chat_id=999)

    with pytest.raises(GroupChatAlreadyRegisteredException):
        service.register_team('Duplicate', group_chat_id=999)


def test_find_team_by_spectator_password_matches_exactly(data_access, default_team):
    service = TeamService(data_access)

    found = service.find_team_by_spectator_password(default_team.spectator_password)

    assert found is not None
    assert found.doc_id == default_team.doc_id


def test_find_team_by_spectator_password_is_case_sensitive(data_access, default_team):
    service = TeamService(data_access)

    assert service.find_team_by_spectator_password(default_team.spectator_password.lower()) is None


def test_team_without_password_never_matches(data_access):
    service = TeamService(data_access)
    service.register_team('No Password', group_chat_id=999)

    assert service.find_team_by_spectator_password('') is None
    assert service.find_team_by_spectator_password(None) is None


def test_set_spectator_password_rejects_another_teams_password(data_access, default_team):
    service = TeamService(data_access)
    other = service.register_team('Other', group_chat_id=999)

    with pytest.raises(SpectatorPasswordAlreadyTakenException):
        service.set_spectator_password(other, default_team.spectator_password)


def test_set_spectator_password_persists_to_store(data_access):
    service = TeamService(data_access)
    team = service.register_team('Other', group_chat_id=999)

    service.set_spectator_password(team, 'freshPassword')

    # A NEW instance reads from the store, not this instance's cache.
    reloaded = TeamService(data_access)
    assert reloaded.find_team_by_spectator_password('freshPassword').doc_id == team.doc_id


def test_current_team_returns_the_context_team(data_access, default_team):
    service = TeamService(data_access)

    assert service.current_team().doc_id == default_team.doc_id


def test_register_team_invalidates_cache_on_same_instance(data_access):
    service = TeamService(data_access)
    service.get_all_teams()  # prime the cache

    team = service.register_team('Other', group_chat_id=999)

    assert any(t.doc_id == team.doc_id for t in service.get_all_teams())


def test_set_spectator_password_rejects_empty_and_reserved(data_access, default_team):
    from framework.Services.TeamService import TeamService
    from Utils.CustomExceptions import SpectatorPasswordNotAllowedException
    import pytest
    service = TeamService(data_access)
    team = service.get_all_teams()[0]
    for bad in ('', 'help', 'HELP', '/help'):
        with pytest.raises(SpectatorPasswordNotAllowedException):
            service.set_spectator_password(team, bad)
    # Nothing persisted, cache still serves the stored truth.
    assert TeamService(data_access).get_all_teams()[0].spectator_password == default_team.spectator_password
