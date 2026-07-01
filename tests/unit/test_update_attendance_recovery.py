"""Unit: DataAccess.update_attendance recovers when the record vanishes mid-flight.

get_event_attendance_doc_id can return a doc that is then deleted before the write
(a race). The write raises ObjectNotFoundException; update_attendance must recreate
the record so the player's vote isn't silently lost, rather than letting the error
bubble up and drop the vote.
"""
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from databaseEntities.Attendance import Attendance
from Utils.CustomExceptions import ObjectNotFoundException


class _FakeDocRef:
    def __init__(self, doc_id):
        self.id = doc_id


class _RaceRepository:
    """Finds the record, but the update fails because it was deleted in between."""

    def __init__(self):
        self.added = []

    def get_event_attendance_doc_id(self, attendance, table):
        return "stale-doc-id"

    def update(self, attendance, table):
        raise ObjectNotFoundException(str(table), attendance.doc_id)

    def add(self, attendance, table):
        self.added.append(attendance)
        return (None, _FakeDocRef("recreated-doc-id"))


def test_update_attendance_recreates_record_when_write_races_a_delete(data_access):
    repo = _RaceRepository()
    data_access.firebase_repository = repo
    attendance = Attendance("user-1", "event-1", AttendanceState.YES)

    result = data_access.update_attendance(attendance, Event.GAME)

    # Recovered: the vote is preserved as a freshly created record, no exception raised.
    assert result.doc_id == "recreated-doc-id"
    assert len(repo.added) == 1
    assert repo.added[0].state == AttendanceState.YES


def test_update_attendance_still_creates_when_no_record_exists(data_access):
    """The plain add path (no existing record) is unaffected by the recovery branch."""

    class _NoRecordRepository(_RaceRepository):
        def get_event_attendance_doc_id(self, attendance, table):
            return None

        def update(self, attendance, table):
            raise AssertionError("update must not be called when no record exists")

    repo = _NoRecordRepository()
    data_access.firebase_repository = repo
    attendance = Attendance("user-2", "event-2", AttendanceState.NO)

    result = data_access.update_attendance(attendance, Event.GAME)

    assert result.doc_id == "recreated-doc-id"
    assert len(repo.added) == 1
