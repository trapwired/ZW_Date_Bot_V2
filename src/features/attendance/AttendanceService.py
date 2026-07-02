"""Application service for the attendance slice.

Owns the data orchestration for a player changing their attendance on an event,
so EditCallbackNode stays thin and Telegram-facing.
"""
from data.DataAccess import DataAccess

from Enums.Event import Event

from domain.entities.Attendance import Attendance


class AttendanceService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def set_attendance(self, telegram_id: int, event_type: Event, doc_id: str, state):
        """Persist the player's attendance for an event; returns (attendance, event) for rendering."""
        user = self.data_access.get_user(telegram_id)
        attendance = self.data_access.update_attendance(Attendance(user.doc_id, doc_id, state), event_type)
        event = self.data_access.get_event(event_type, doc_id)
        return attendance, event

    def get_attendance(self, telegram_id: int, doc_id: str, event_type: Event) -> Attendance:
        return self.data_access.get_attendance(telegram_id, doc_id, event_type)

    def get_own_attendances(self, telegram_id: int) -> dict:
        """All of one player's attendances across every event type, keyed by event doc_id."""
        user = self.data_access.get_user(telegram_id)
        return self.data_access.get_all_event_attendances(user)

    def yes_count(self, doc_id: str, event_type: Event) -> int:
        yes, _, _ = self.data_access.get_stats_event(doc_id, event_type)
        return len(yes)
