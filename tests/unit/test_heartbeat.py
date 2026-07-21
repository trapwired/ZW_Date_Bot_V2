"""The dead-man ping must be strictly opt-in (env-driven): unset URL = no job, so
local runs and CI never ping; set URL = one repeating job on the bot's loop."""
from types import SimpleNamespace

from framework import Heartbeat


class FakeJobQueue:
    def __init__(self):
        self.repeating = []

    def run_repeating(self, callback, interval, first):
        self.repeating.append(SimpleNamespace(callback=callback, interval=interval, first=first))


def test_no_url_registers_nothing(monkeypatch):
    monkeypatch.delenv(Heartbeat.HEALTHCHECK_URL_ENV, raising=False)
    queue = FakeJobQueue()

    assert Heartbeat.register(queue) is False
    assert queue.repeating == []


def test_url_registers_repeating_ping(monkeypatch):
    monkeypatch.setenv(Heartbeat.HEALTHCHECK_URL_ENV, 'https://hc-ping.com/fake-uuid')
    queue = FakeJobQueue()

    assert Heartbeat.register(queue) is True
    assert len(queue.repeating) == 1
    assert queue.repeating[0].interval == Heartbeat.PING_INTERVAL_SECONDS
