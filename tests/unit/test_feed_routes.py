"""The feed's HTTP surface (plan §6, §10) on aiohttp's test server, backed by the real
service stack: status codes, headers, the uniform 404 and the 500 without alert."""
import asyncio
import logging
import threading

import pytest
from aiohttp.test_utils import TestClient, TestServer

from Enums.Role import Role
from Enums.UserState import UserState

from features.calendarfeed import FeedRoutes
from features.calendarfeed.FeedRoutes import NOT_FOUND_TEXT, build_feed_app

from tests.helpers import seed_user

MEMBER_ID = 7200
VALID_LOOKING = 'A' * 40


@pytest.fixture
def calendar_feed_service(services):
    return services['calendar_feed_service']


def file_name(link) -> str:
    return link.url.rsplit('/', 1)[1]


async def test_feed_is_served_as_an_inline_calendar(data_access, calendar_feed_service, game):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = calendar_feed_service.issue_link(MEMBER_ID)

    async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
        response = await client.get(f'/cal/{file_name(link)}')
        body = await response.text()

    assert response.status == 200
    assert response.headers['Content-Type'] == 'text/calendar; charset=utf-8'
    assert response.headers['Cache-Control'] == 'no-cache'
    assert response.headers['Content-Disposition'] == 'inline; filename="zw-date-bot.ics"'
    assert body.startswith('BEGIN:VCALENDAR\r\n')
    assert 'rivals fc' in body


@pytest.mark.parametrize('requested', [
    VALID_LOOKING + '.ics',       # unknown
    'tooshort.ics',
    VALID_LOOKING,                # no .ics
    VALID_LOOKING + 'A.ics',      # one char too many
    VALID_LOOKING + '.ics.ics',
])
async def test_every_miss_is_the_same_404(data_access, calendar_feed_service, requested):
    async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
        response = await client.get(f'/cal/{requested}')
        body = await response.text()

    _assert_not_found(response, body)


@pytest.mark.parametrize('method, path', [
    ('GET', '/cal/'),
    ('GET', '/cal/a/b.ics'),
    ('GET', f'/cal/{VALID_LOOKING}.ics/'),
    ('POST', f'/cal/{VALID_LOOKING}.ics'),
    ('POST', '/cal/'),
])
async def test_everything_else_under_cal_is_the_same_404(data_access, calendar_feed_service, method, path):
    async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
        response = await client.request(method, path)
        body = await response.text()

    _assert_not_found(response, body)


async def test_post_to_a_live_link_is_a_404_too(data_access, calendar_feed_service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    link = calendar_feed_service.issue_link(MEMBER_ID)

    async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
        response = await client.post(f'/cal/{file_name(link)}')
        body = await response.text()

    _assert_not_found(response, body)


async def test_rotated_link_is_a_404(data_access, calendar_feed_service):
    seed_user(data_access, MEMBER_ID, Role.PLAYER, UserState.DEFAULT)
    old = calendar_feed_service.issue_link(MEMBER_ID)
    calendar_feed_service.issue_link(MEMBER_ID)

    async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
        response = await client.get(f'/cal/{file_name(old)}')
        body = await response.text()

    _assert_not_found(response, body)


async def test_health_probe(calendar_feed_service):
    async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
        response = await client.get('/healthz')
        body = await response.text()

    assert response.status == 200
    assert response.headers['Content-Type'].startswith('text/plain')
    assert body == 'ok'


async def test_failing_feed_is_a_logged_500_without_telegram_alert(data_access, calendar_feed_service, bot,
                                                                   monkeypatch, caplog):
    def broken_lookup(_token_hash):
        raise RuntimeError('database is gone')

    monkeypatch.setattr(data_access, 'find_calendar_token_by_hash', broken_lookup)

    with caplog.at_level(logging.ERROR):
        async with TestClient(TestServer(build_feed_app(calendar_feed_service))) as client:
            response = await client.get(f'/cal/{VALID_LOOKING}.ics')

    assert response.status == 500
    assert response.headers['Content-Type'] == 'text/plain; charset=utf-8'
    assert 'database is gone' in caplog.text  # with traceback
    assert bot.sent == []


class _BlockingFeedService:
    """render_feed parks in its worker thread until released, counting how many are parked at once."""

    def __init__(self):
        self.release = threading.Event()
        self._lock = threading.Lock()
        self.running = 0
        self.peak = 0

    def render_feed(self, _file_name):
        with self._lock:
            self.running += 1
            self.peak = max(self.peak, self.running)
        self.release.wait(timeout=5)
        with self._lock:
            self.running -= 1
        return None


async def test_concurrent_feed_renders_are_capped(monkeypatch):
    # A fresh semaphore: the module-level one would bind to the first test loop that contends on it.
    monkeypatch.setattr(FeedRoutes, 'CONCURRENT_FEED_RENDERS', asyncio.Semaphore(2))
    service = _BlockingFeedService()

    async with TestClient(TestServer(build_feed_app(service))) as client:
        requests = [asyncio.ensure_future(client.get(f'/cal/{VALID_LOOKING}.ics')) for _ in range(5)]
        try:
            await _until(lambda: service.running == 2)
            await asyncio.sleep(0.2)  # time for a third render to start if the cap were missing
            assert service.running == 2
        finally:
            service.release.set()
        responses = await asyncio.gather(*requests)

    assert service.peak == 2
    assert [response.status for response in responses] == [404] * 5


async def _until(condition, timeout: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        assert asyncio.get_running_loop().time() < deadline, 'condition never became true'
        await asyncio.sleep(0.01)


def _assert_not_found(response, body: str) -> None:
    assert response.status == 404
    assert response.headers['Content-Type'] == 'text/plain; charset=utf-8'
    assert response.headers['Cache-Control'] == 'no-store'
    assert body == NOT_FOUND_TEXT
