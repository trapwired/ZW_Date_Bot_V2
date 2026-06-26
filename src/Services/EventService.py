"""Application service for the event-management slice.

Owns the event-management data orchestration (drafts, event reads and updates,
attendance reset, recipient lookup) so the event nodes stay thin and
Telegram-facing. Presentation (sending messages, building markup) stays in the
nodes. (Event deletion moves here with the callback-event-node slice.)
"""
from Data.DataAccess import DataAccess

from Enums.CallbackOption import CallbackOption
from Enums.Event import Event

from databaseEntities.TempData import TempData


class EventService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    # --- event drafts (the add-event wizard scratch state) ---

    def get_draft(self, user_id: str) -> TempData:
        return self.data_access.get_temp_data(user_id)

    def save_draft(self, draft: TempData) -> None:
        self.data_access.update(draft)

    def discard_draft(self, draft: TempData) -> None:
        self.data_access.delete(draft)

    def finalize_draft(self, draft: TempData):
        """Persist the finished event and discard the draft in one step, so a saved
        draft can never linger after its event exists."""
        event = self.data_access.add(draft.get_finished_event())
        self.data_access.delete(draft)
        return event

    # --- existing events ---

    def get_event(self, event_type: Event, doc_id: str):
        return self.data_access.get_event(event_type, doc_id)

    def update_field(self, event_type: Event, doc_id: str, new_value, field_type: CallbackOption):
        return self.data_access.update_event_field(event_type, doc_id, new_value, field_type)

    def reset_attendance(self, event_type: Event, doc_id: str) -> None:
        self.data_access.reset_all_player_event_attendance(event_type, doc_id)

    def get_all_players(self) -> list:
        return self.data_access.get_all_players()
