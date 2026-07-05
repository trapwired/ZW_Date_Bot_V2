"""Team stamp for inline callback data.

Callback authorization gates on the presser's role, and the ambient tenant is the
presser's team - so a forwarded admin button (roles, trainer toggles, ...) pressed
by an admin of ANOTHER team would write foreign ids into the presser's own team.
Stamping the rendering team's id into the callback data lets NodeHandler drop any
press whose stamp doesn't match the presser's team - one mechanism for every
stamped menu instead of per-button roster checks.

The stamp is the LAST '#'-segment, marked 't:' (Firestore ids are alphanumeric, so
the marker cannot collide with a real argument). Buttons rendered before this
existed carry no stamp and stay usable - they keep the old, unguarded behavior
until their menus get re-rendered.

Only the admin channels (AP#, ROLES#) are stamped: their payloads (telegram ids,
global user doc ids) are valid in ANY tenant. EV# already fails closed cross-team
on team-scoped doc ids, and ONB# is for teamless users - both stay unstamped on
purpose.
"""
from data.TenantContext import current_team_id

DELIMITER = '#'
MARKER = 't:'


def stamp(data: str) -> str:
    """Append the ambient team's id. Fails loud (MissingTenantContextError) outside
    a tenant context - a stamped menu rendered without one would silently disable
    the guard for every button on it."""
    return f'{data}{DELIMITER}{MARKER}{current_team_id()}'


def strip(data: str) -> str:
    bare, _ = _split(data)
    return bare


def stamped_team(data: str) -> str | None:
    _, team_id = _split(data)
    return team_id


def _split(data: str) -> tuple[str, str | None]:
    head, _, tail = data.rpartition(DELIMITER)
    if tail.startswith(MARKER):
        return head, tail[len(MARKER):]
    return data, None
