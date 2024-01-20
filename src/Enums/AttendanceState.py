from enum import IntEnum


class AttendanceState(IntEnum):
    UNSURE = 0
    YES = 1
    NO = 2
    # 3 already taken (CALENDAR)