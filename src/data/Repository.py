"""THE storage seam (Stage B of the VPS migration): every persistence backend
implements this surface, and DataAccess talks only to it. Swapping backends is
config (`[Database] backend`), never a code edit.

Contracts every backend must honour (DataAccess depends on all three):
- Query methods return "rows": any object with `.id` and `.to_dict()`.
- `add` returns the new row's id as a str.
- Reads/updates against a missing document raise ObjectNotFoundException.
"""
from abc import ABC, abstractmethod

from Enums.Event import Event
from Enums.Role import Role
from Enums.Table import Table

from domain.entities.Attendance import Attendance
from domain.entities.DatabaseEntity import DatabaseEntity
from domain.entities.Game import Game
from domain.entities.Settings import Settings
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.TempData import TempData
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training
from domain.entities.UsersToState import UsersToState


class Repository(ABC):
    """What a storage backend must provide. Method semantics are pinned by the
    contract tests (tests/contract), which run every backend side by side."""

    @abstractmethod
    def get_document(self, doc_id: str, table: Table):
        ...

    @abstractmethod
    def get_user(self, telegram_id_or_doc_id: int | str) -> TelegramUser | None:
        ...

    @abstractmethod
    def get_user_state(self, user: TelegramUser) -> UsersToState | None:
        ...

    @abstractmethod
    def get_game(self, doc_id: str) -> Game | None:
        ...

    @abstractmethod
    def get_training(self, doc_id: str) -> Training | None:
        ...

    @abstractmethod
    def get_timekeeping(self, doc_id: str) -> TimekeepingEvent | None:
        ...

    @abstractmethod
    def get_team(self, doc_id: str) -> Team:
        ...

    @abstractmethod
    def get_all_teams(self) -> list[Team]:
        ...

    @abstractmethod
    def get_player_metric(self, user: TelegramUser):
        ...

    @abstractmethod
    def get_temp_data(self, user_doc_id: str) -> TempData:
        ...

    @abstractmethod
    def get_settings(self) -> Settings | None:
        ...

    @abstractmethod
    def set_settings(self, settings: Settings):
        ...

    @abstractmethod
    def get_future_events(self, table: Table) -> list:
        ...

    @abstractmethod
    def get_attendance_list(self, doc_id: str, table: Table):
        ...

    @abstractmethod
    def get_attendance(self, user: TelegramUser, event_doc_id: str, table: Table):
        ...

    @abstractmethod
    def get_all_user_event_attendance(self, user: TelegramUser, event_type: Event):
        ...

    @abstractmethod
    def get_all_event_attendances(self, event_type: Event, relevant_doc_ids: list[str]):
        ...

    @abstractmethod
    def get_all_relevant_event_ids(self, event_type: Event):
        ...

    @abstractmethod
    def get_all_player_metrics(self):
        ...

    @abstractmethod
    def get_users_to_state_by_role(self, role: Role):
        ...

    @abstractmethod
    def get_admins_to_state(self):
        ...

    @abstractmethod
    def get_users_to_state_by_team(self, team_id: str):
        ...

    @abstractmethod
    def has_any_docs(self, table: Table) -> bool:
        ...

    @abstractmethod
    def delete_team(self, doc_id: str):
        ...

    @abstractmethod
    def get_all_active_players_to_state(self):
        ...

    @abstractmethod
    def get_event_attendance_doc_id(self, attendance: Attendance, table: Table):
        ...

    @abstractmethod
    def add(self, new_object: DatabaseEntity, table: Table) -> str:
        ...

    @abstractmethod
    def update(self, db_object: DatabaseEntity, table: Table):
        ...

    @abstractmethod
    def update_user_state(self, user_to_state: UsersToState):
        ...

    @abstractmethod
    def update_user_state_via_user_id(self, user_to_state: UsersToState):
        ...

    @abstractmethod
    def update_user_via_telegram_id(self, user: TelegramUser):
        ...

    @abstractmethod
    def delete_temp_data(self, temp_data: TempData):
        ...

    @abstractmethod
    def delete_game(self, doc_id: str):
        ...

    @abstractmethod
    def delete_training(self, doc_id: str):
        ...

    @abstractmethod
    def delete_timekeeping(self, doc_id: str):
        ...

    @abstractmethod
    def delete_event_attendances(self, event_type: Event, event_doc_id: str):
        ...

    @abstractmethod
    def delete_all_player_metrics(self) -> int:
        ...

    @abstractmethod
    def reset_all_player_event_attendance(self, doc_id: str, table: Table):
        ...
