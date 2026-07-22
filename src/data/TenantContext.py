"""The ambient tenant context: which team's data the current unit of work (update,
scheduled job iteration, migration step) operates on.

Lives in data/ so the repository backends can consume it without a layering cycle.
Fail-closed by design: touching a team-scoped collection with no team resolved
raises instead of reading across tenants (see ADR 0001).
"""
from contextlib import contextmanager
from contextvars import ContextVar, Token

_current_team_id: ContextVar[str | None] = ContextVar('current_team_id', default=None)


class MissingTenantContextError(Exception):
    """A team-scoped collection was touched with no team resolved."""


def set_current_team(team_id: str | None) -> Token:
    return _current_team_id.set(team_id)


def reset_current_team(token: Token) -> None:
    _current_team_id.reset(token)


def current_team_id() -> str:
    team_id = _current_team_id.get()
    if team_id is None:
        raise MissingTenantContextError('no team resolved for this unit of work')
    return team_id


def peek_team_id() -> str | None:
    """The current team id or None - for logging/diagnostics, never for scoping."""
    return _current_team_id.get()


@contextmanager
def team_context(team_id: str):
    token = set_current_team(team_id)
    try:
        yield
    finally:
        reset_current_team(token)
