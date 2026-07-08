from enum import IntEnum


class Role(IntEnum):
    """Membership state of a user within their team. Admin is NOT a role: it is the
    orthogonal UsersToState.is_admin flag, so e.g. a retired player can keep running
    the team without receiving player reminders (ADR 0005)."""
    INIT = -1
    PLAYER = 0
    SPECTATOR = 10
    RETIRED = 100
    INACTIVE = 101
    REJECTED = 999


# Wire/DB value of the retired ADMIN enum member; pre-refactor documents and
# in-flight inline buttons still carry it (healed to PLAYER + is_admin).
LEGACY_ADMIN_ROLE_VALUE = 42

# Roles an admin can hand out via the roles menu, in display order.
ASSIGNABLE_ROLES = [Role.PLAYER, Role.RETIRED, Role.INACTIVE]
