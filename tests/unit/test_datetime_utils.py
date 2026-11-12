import pandas as pd

from Utils import DateTimeUtils
from tests.helpers import host_clock_in


def test_local_now_is_the_current_zurich_time_on_a_utc_host():
    with host_clock_in('UTC'):
        before = pd.Timestamp.now(tz='UTC')
        local_now = DateTimeUtils.get_local_now()
        after = pd.Timestamp.now(tz='UTC')

    assert str(local_now.tz) == 'Europe/Zurich'
    assert before <= local_now <= after
