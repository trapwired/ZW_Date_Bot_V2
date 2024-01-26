from enum import IntEnum

from Enums.AttendanceState import AttendanceState


class CallbackOption(IntEnum):
    UNSURE = AttendanceState.UNSURE
    YES = AttendanceState.YES
    NO = AttendanceState.NO

    UPDATE = 10
    DELETE = 11

    LOCATION = 20
    OPPONENT = 21
    DATETIME = 22

    Back = 30

    RESTART = 40
    CANCEL = 41
    SAVE = 42


