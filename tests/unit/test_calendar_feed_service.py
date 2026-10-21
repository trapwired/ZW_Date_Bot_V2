"""CalendarFeedService (plan §6, §10): issuing and rotating links, link status, and the
feed a link renders per role - on the real DataAccess over the in-memory backend."""
import logging
from datetime import timedelta
from urllib.parse import quote

import pandas as pd
import pytest

from Enums.AttendanceState import AttendanceState
from Enums.Role import Role
from Enums.Table import Table
from Enums.UserState import UserState

from data.TenantContext import team_context
from domain.Season import get_current_season_dates
from domain.calendar.Tokens import hash_token
from domain.entities.Game import Game
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training

from features.calendarfeed.CalendarFeedService import CalendarFeedConfig, CalendarFeedService

from tests.helpers import seed_user, set_attendance

MEMBER_ID = 7100
FUTURE = pd.Timestamp('2030-12-24 18:30', tz='Europe/Zurich')


@pytest.fixture
def service(data_access):
    return CalendarFeedService(data_access, CalendarFeedConfig('http://test.local', 8080))


def file_name(link) -> str:
    return link.url.rsplit('/', 1)[1]


def raw_token(link) -> str:
    return file_name(link).removesuffix('.ics')


def unfolded(body: str) -> str:
    return body.replace('\r\n ', '')


def summaries(body: str) -> list[str]:
    return [line.removeprefix('SUMMARY:') for line in unfolded(body).split('\r\n') if line.startswith('SUMMARY:')]


def add_game(data_access, opponent: str, when=FUTURE) -> Game:
    return data_access.add(Game(when, 'home arena', opponent))


# --- issuing, rotating, status ---------------------------------------------------------

def test_issued_link_points_at_the_public_origin(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)

    link = service.issue_link(MEMBER_ID)

    assert link.url == f'http://test.local/cal/{raw_token(link)}.ics'
    assert len(raw_token(link)) == 40
    assert link.google_url == ('https://www.google.com/calendar/render?cid='
                               + quote(f'webcal://test.local/cal/{raw_token(link)}.ics', safe=''))


def test_issued_link_keeps_the_token_out_of_its_repr(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)

    link = service.issue_link(MEMBER_ID)

    assert raw_token(link) not in repr(link)


def test_only_the_hash_is_stored(data_access, service):
    member = seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)

    link = service.issue_link(MEMBER_ID)

    assert data_access.get_calendar_token(member.user_id).token_hash == hash_token(raw_token(link))
    assert raw_token(link) not in repr(data_access.repository.db.storage)


def test_rotation_kills_the_old_link(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    old = service.issue_link(MEMBER_ID)

    new = service.issue_link(MEMBER_ID)

    assert service.render_feed(file_name(old)) is None
    assert service.render_feed(file_name(new)).startswith('BEGIN:VCALENDAR\r\n')


def test_status_is_none_before_the_first_link(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)

    assert service.link_status(MEMBER_ID) is None


def test_status_reports_creation_and_last_fetch(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = service.issue_link(MEMBER_ID)

    fresh = service.link_status(MEMBER_ID)
    service.render_feed(file_name(link))
    fetched = service.link_status(MEMBER_ID)

    assert fresh.created_at.date() == pd.Timestamp.now(tz='Europe/Zurich').date()
    assert fresh.last_used_at is None
    assert fetched.last_used_at is not None


def test_a_failing_stamp_never_breaks_the_feed(data_access, service, monkeypatch, caplog):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = service.issue_link(MEMBER_ID)

    def broken_touch(*_args):
        raise RuntimeError('db hiccup')

    monkeypatch.setattr(data_access, 'touch_calendar_token', broken_touch)
    with caplog.at_level(logging.WARNING):
        body = service.render_feed(file_name(link))

    assert body.startswith('BEGIN:VCALENDAR\r\n')
    assert 'last_used_at' in caplog.text


# --- what the feed shows, per role -------------------------------------------------------

@pytest.mark.parametrize('role', [Role.PLAYER, Role.RETIRED])
def test_member_who_can_answer_sees_own_answers(data_access, service, role):
    member = seed_user(data_access, MEMBER_ID, role, UserState.DEFAULT)
    yes, unsure, declined = add_game(data_access, 'yes fc'), add_game(data_access, 'unsure fc'), \
        add_game(data_access, 'declined fc')
    add_game(data_access, 'silent fc')
    set_attendance(data_access, member.user_id, yes.doc_id, AttendanceState.YES)
    set_attendance(data_access, member.user_id, unsure.doc_id, AttendanceState.UNSURE)
    set_attendance(data_access, member.user_id, declined.doc_id, AttendanceState.NO)
    data_access.add(TimekeepingEvent(FUTURE, 'eventhalle', 2))

    body = service.render_feed(file_name(service.issue_link(MEMBER_ID)))

    assert sorted(summaries(body)) == sorted([
        '✅ Handball Game Züri West (yes fc)',
        '❓ Handball Game Züri West (unsure fc)',
        '❓ Handball Game Züri West (silent fc)',
        '❓ Handball Timekeeping Züri West',
    ])


def test_spectator_sees_games_and_trainings_unmarked(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.SPECTATOR, UserState.DEFAULT)
    add_game(data_access, 'rivals fc')
    data_access.add(Training(FUTURE, 'gym'))
    data_access.add(TimekeepingEvent(FUTURE, 'eventhalle', 2))

    body = service.render_feed(file_name(service.issue_link(MEMBER_ID)))

    assert sorted(summaries(body)) == ['Handball Game Züri West (rivals fc)', 'Handball Training Züri West']
    assert 'DESCRIPTION' not in body


def test_inactive_member_gets_no_feed(data_access, service):
    member = seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = service.issue_link(MEMBER_ID)
    member.role = Role.INACTIVE
    data_access.update(member)

    assert service.render_feed(file_name(link)) is None


@pytest.mark.parametrize('role', [Role.INACTIVE, Role.REJECTED])
def test_admin_keeps_the_feed_whatever_their_role(data_access, service, role):
    # Same gate as the events menu (Audience.EVERYONE): an admin is let in regardless of role.
    member = seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    link = service.issue_link(MEMBER_ID)
    member.role = role
    data_access.update(member)

    assert service.render_feed(file_name(link)).startswith('BEGIN:VCALENDAR\r\n')


def test_member_without_team_gets_no_feed(data_access, service):
    member = seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = service.issue_link(MEMBER_ID)
    member.team_id = None
    data_access.update(member)

    assert service.render_feed(file_name(link)) is None


def test_window_is_the_current_season_including_its_past(data_access, service):
    seed_user(data_access, MEMBER_ID, Role.SPECTATOR, UserState.DEFAULT)
    season_start = pd.Timestamp(get_current_season_dates()[0], tz='Europe/Zurich')
    add_game(data_access, 'last season fc', when=season_start - timedelta(hours=1))
    add_game(data_access, 'early this season fc', when=season_start + timedelta(hours=1))

    body = service.render_feed(file_name(service.issue_link(MEMBER_ID)))

    assert summaries(body) == ['Handball Game Züri West (early this season fc)']


def test_feed_speaks_the_member_language(data_access, service, game):
    member = seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    member.language = 'de'
    data_access.update(member)

    body = service.render_feed(file_name(service.issue_link(MEMBER_ID)))

    assert 'DESCRIPTION:Deine Antwort' in unfolded(body)


def test_feed_falls_back_to_the_team_language(data_access, service, default_team, game):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    default_team.language = 'fr'
    data_access.update(default_team)

    body = service.render_feed(file_name(service.issue_link(MEMBER_ID)))

    assert 'DESCRIPTION:Ta réponse' in unfolded(body)


def test_feed_resolves_the_team_without_an_ambient_tenant(data_access, service, game):
    # The HTTP thread has no tenant set; the token alone must lead to the right team.
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = service.issue_link(MEMBER_ID)

    with team_context(None):
        body = service.render_feed(file_name(link))

    assert summaries(body) == ['❓ Handball Game Züri West (rivals fc)']


# --- misses and config -------------------------------------------------------------------

@pytest.mark.parametrize('table, doc_id_of', [
    (Table.USERS_TABLE, lambda member: member.user_id),
    (Table.USERS_TO_STATE_TABLE, lambda member: member.doc_id),
    (Table.TEAMS_TABLE, lambda member: member.team_id),
], ids=['user', 'user state', 'team'])
def test_token_with_a_dangling_row_is_a_miss_not_an_error(data_access, service, table, doc_id_of):
    member = seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = service.issue_link(MEMBER_ID)
    # Straight at the store: the token row survives, the row it points through is gone.
    data_access.repository._collection(table).document(doc_id_of(member)).delete()

    assert service.render_feed(file_name(link)) is None


@pytest.mark.parametrize('name', [
    'A' * 40 + '.ics',   # well-formed, never issued
    'short.ics',
    'A' * 40,
    'A' * 41 + '.ics',
    'A' * 40 + '.ics.ics',
    '',
])
def test_unknown_or_malformed_file_names_render_nothing(data_access, service, name):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    service.issue_link(MEMBER_ID)

    assert service.render_feed(name) is None


class _ApiConfigStub:
    def __init__(self, values: dict):
        self.values = values

    def get_key(self, section, key, default=None):
        return self.values.get((section, key), default)


def test_config_defaults_to_off():
    config = CalendarFeedConfig.from_api_config(_ApiConfigStub({}))

    assert config == CalendarFeedConfig('', 8080)
    assert not config.enabled


def test_config_strips_a_trailing_slash():
    config = CalendarFeedConfig.from_api_config(_ApiConfigStub({
        ('Calendar', 'public_origin'): 'https://zwbot.example.ch/',
        ('Calendar', 'http_port'): '9090',
    }))

    assert config == CalendarFeedConfig('https://zwbot.example.ch', 9090)
    assert config.enabled


def test_disabled_service_reports_disabled(data_access):
    assert not CalendarFeedService(data_access, CalendarFeedConfig('', 8080)).enabled
