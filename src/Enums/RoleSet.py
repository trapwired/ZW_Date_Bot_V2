from enum import Enum

from Enums.Role import Role


class RoleSet(set, Enum):
    REALLY_EVERYONE = {Role.INIT, Role.ADMIN, Role.PLAYER, Role.SPECTATOR, Role.RETIRED, Role.INACTIVE}
    EVERYONE = {Role.ADMIN, Role.PLAYER, Role.SPECTATOR, Role.RETIRED}
    PLAYERS = {Role.ADMIN, Role.PLAYER, Role.RETIRED}
    ACTIVE_PLAYERS = {Role.ADMIN, Role.PLAYER}
    SPECTATORS = {Role.SPECTATOR}
    ADMINS = {Role.ADMIN}
    REJECTED = {Role.REJECTED}
