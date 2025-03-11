from enum import IntEnum


class Role(IntEnum):
    INIT = -1
    PLAYER = 0
    SPECTATOR = 10
    ADMIN = 42
    RETIRED = 100
    INACTIVE = 101
    REJECTED = 999
