from enum import Enum

from Enums.Role import Role


class RoleSet(set, Enum):
    EVERYONE = {Role.ADMIN, Role.PLAYER, Role.SPECTATOR}
    PLAYERS = {Role.ADMIN, Role.PLAYER}
    SPECTATORS = {Role.SPECTATOR}
    ADMINS = {Role.ADMIN}
    REJECTED = {Role.REJECTED}
