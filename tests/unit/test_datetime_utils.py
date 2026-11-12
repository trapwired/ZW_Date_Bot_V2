import time

import pandas as pd
import pytest

from Utils import DateTimeUtils


@pytest.fixture
def process_clock_in_utc(monkeypatch):
    monkeypatch.setenv('TZ', 'UTC')
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_local_now_is_the_current_zurich_time_on_a_utc_host(process_clock_in_utc):
    before = pd.Timestamp.now(tz='UTC')
    local_now = DateTimeUtils.get_local_now()
    after = pd.Timestamp.now(tz='UTC')

    assert str(local_now.tz) == 'Europe/Zurich'
    assert before <= local_now <= after
