"""Unit: the group reminders send one summary per event, not the first event repeated.

Both send_previous_day_training_reminder and send_same_day_game_reminder used to build
their summary from events_to_remind[0] regardless of which event the loop was on, so a
day with two events produced two summaries that both described the first event.
"""
import datetime
from types import SimpleNamespace

import pandas as pd

from framework.Services.SchedulingService import SchedulingService


class _RecordingTelegram:
    def __init__(self):
        self.group_messages = []

    async def send_group_message(self, message):
        self.group_messages.append(message)

    async def report_exception(self, description, error, *args):
        # Surface any swallowed failure instead of letting the test pass silently.
        raise AssertionError(f"{description}: {error!r}")


class _StubDataAccess:
    def __init__(self, games=(), trainings=()):
        self._games = list(games)
        self._trainings = list(trainings)

    def get_all_teams(self):
        # Scheduled jobs iterate teams via _for_each_team; one team makes the body run once.
        return [SimpleNamespace(doc_id="team-1")]

    def get_ordered_games(self):
        return self._games

    def get_ordered_trainings(self):
        return self._trainings

    def get_stats_event(self, doc_id, event_type):
        return ([], [], [])

    def get_names(self, stats):
        return ([], [], [])


def _event(doc_id, day, hour, **extra):
    ts = pd.Timestamp(day.year, day.month, day.day, hour, 0)
    return SimpleNamespace(doc_id=doc_id, timestamp=ts, location="the hall", **extra)


async def test_previous_day_training_reminder_sends_one_summary_per_event(api_config):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    trainings = [_event("t1", tomorrow, 18), _event("t2", tomorrow, 20)]
    telegram = _RecordingTelegram()
    scheduling = SchedulingService(_StubDataAccess(trainings=trainings), telegram, object(), api_config)

    await scheduling.send_previous_day_training_reminder(context=None)

    assert len(telegram.group_messages) == 2
    assert "18:00" in telegram.group_messages[0]
    assert "20:00" in telegram.group_messages[1]


async def test_same_day_game_reminder_sends_one_summary_per_game(api_config):
    today = datetime.date.today()
    games = [_event("g1", today, 14, opponent="rivals"), _event("g2", today, 16, opponent="foes")]
    telegram = _RecordingTelegram()
    scheduling = SchedulingService(_StubDataAccess(games=games), telegram, object(), api_config)

    await scheduling.send_same_day_game_reminder(context=None)

    assert len(telegram.group_messages) == 2
    assert "14:00" in telegram.group_messages[0]
    assert "16:00" in telegram.group_messages[1]
