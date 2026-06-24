from enum import IntEnum


class Role(IntEnum):
    INIT = -1
    PLAYER = 0
    SPECTATOR = 10
    ADMIN = 42
    RETIRED = 100
    INACTIVE = 101
    REJECTED = 999


# Roles an admin can browse and hand out via /assign_roles, in display order.
ASSIGNABLE_ROLES = [Role.PLAYER, Role.ADMIN, Role.RETIRED, Role.INACTIVE]
