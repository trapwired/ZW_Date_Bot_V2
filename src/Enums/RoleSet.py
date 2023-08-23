from enum import Enum

from Enums.Role import Role


class RoleSet(set, Enum):
    REALLY_EVERYONE = {Role.INIT, Role.ADMIN, Role.PLAYER, Role.SPECTATOR}
    EVERYONE = {Role.ADMIN, Role.PLAYER, Role.SPECTATOR}
    PLAYERS = {Role.ADMIN, Role.PLAYER}
    SPECTATORS = {Role.SPECTATOR}
    ADMINS = {Role.ADMIN}
    REJECTED = {Role.REJECTED}
