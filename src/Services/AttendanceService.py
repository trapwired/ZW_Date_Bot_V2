"""Application service for the attendance slice.

Owns the data orchestration for a player changing their attendance on an event,
so EditCallbackNode stays thin and Telegram-facing.
"""
from Data.DataAccess import DataAccess

from Enums.Event import Event

from databaseEntities.Attendance import Attendance


class AttendanceService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def set_attendance(self, telegram_id: int, event_type: Event, doc_id: str, state):
        """Persist the player's attendance for an event; returns (attendance, event) for rendering."""
        user = self.data_access.get_user(telegram_id)
        attendance = self.data_access.update_attendance(Attendance(user.doc_id, doc_id, state), event_type)
        event = self.data_access.get_event(event_type, doc_id)
        return attendance, event
