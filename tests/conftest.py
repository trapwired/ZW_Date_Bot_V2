"""Test harness for ZW_Date_Bot_V2.

Doubles live at the two external boundaries — Firestore (``self.db``) and
telegram.Bot — so everything we actually own (DataAccess, FirebaseRepository,
Services, Nodes, NodeHandler) runs for real under test. See tests/doubles/.
"""
import pytest

from tests.doubles.fake_firestore import FakeFirestoreClient, FakeFieldFilter
from tests.doubles.fake_bot import FakeBot


@pytest.fixture
def fake_firestore():
    return FakeFirestoreClient()


@pytest.fixture
def bot():
    return FakeBot()


@pytest.fixture
def api_config():
    from Utils.ApiConfig import ApiConfig
    return ApiConfig()


@pytest.fixture
def data_access(monkeypatch, fake_firestore, api_config):
    """Real DataAccess + FirebaseRepository on top of the in-memory Firestore client.

    Registers a single default team and sets it as the ambient tenant context, so the
    team-scoped collections most tests touch are reachable. The /start flow rebinds the
    same team via find_team_by_group_chat ([Telegram] group_chat_id)."""
    import firebase_admin
    import firebase_admin.credentials  # noqa: F401 - ensure submodule is importable before patching
    import data.FirebaseRepository as fr

    monkeypatch.setattr("firebase_admin.credentials.Certificate", lambda *a, **k: object())
    monkeypatch.setattr("firebase_admin.initialize_app", lambda *a, **k: object())
    monkeypatch.setattr(fr.firestore, "client", lambda app: fake_firestore)
    monkeypatch.setattr(fr, "FieldFilter", FakeFieldFilter)

    from data.DataAccess import DataAccess
    from domain.entities.Team import Team
    from data.TenantContext import set_current_team, reset_current_team

    data_access = DataAccess(api_config)
    team = data_access.add(Team('Züri West',
                                group_chat_id=int(api_config.get_key('Telegram', 'group_chat_id')),
                                spectator_password=api_config.get_key('Chats', 'SPECTATOR_PASSWORD')))
    token = set_current_team(team.doc_id)
    try:
        yield data_access
    finally:
        reset_current_team(token)


@pytest.fixture
def default_team(data_access):
    """The team the data_access fixture registered and made the ambient context."""
    return data_access.get_all_teams()[0]


@pytest.fixture
def game(data_access):
    """A future game most attendance/trigger tests can share."""
    from domain.entities.Game import Game
    from domain.EventDateTimeParser import parse
    return data_access.add(Game(parse("24.12.2030 18:30").value, "home arena", "rivals fc"))


@pytest.fixture
def services(data_access, bot, api_config):
    """The service stack, wired exactly like main.initialize_services but with the fake bot."""
    from framework.Services.UserStateService import UserStateService
    from framework.Services.TelegramService import TelegramService
    from features.attendance.IcsService import IcsService
    from framework.Services.TriggerService import TriggerService
    from features.eventmgmt.EventService import EventService
    from features.attendance.AttendanceService import AttendanceService
    from features.roles.RoleService import RoleService
    from features.website.WebsiteService import WebsiteService
    from features.stats.StatisticsService import StatisticsService

    user_state_service = UserStateService(data_access)
    telegram_service = TelegramService(bot, api_config, user_state_service)
    return {
        "user_state_service": user_state_service,
        "telegram_service": telegram_service,
        "ics_service": IcsService(data_access),
        "trigger_service": TriggerService(data_access, telegram_service),
        "event_service": EventService(data_access),
        "attendance_service": AttendanceService(data_access),
        "role_service": RoleService(data_access),
        "website_service": WebsiteService(data_access),
        "statistics_service": StatisticsService(data_access),
    }


@pytest.fixture
def node_handler(bot, api_config, data_access, services):
    from framework.NodeHandler import NodeHandler
    return NodeHandler(
        bot, api_config,
        services["telegram_service"], services["user_state_service"],
        services["ics_service"], data_access, services["trigger_service"], services["event_service"],
        services["attendance_service"], services["role_service"], services["website_service"],
        services["statistics_service"],
    )
