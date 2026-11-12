from datetime import datetime

import pandas as pd

from domain.Season import get_current_season_dates
from Utils import DateTimeUtils


def test_the_season_turns_over_on_the_zurich_date(monkeypatch):
    first_hour_of_july_in_zurich = pd.Timestamp(2027, 7, 1, 0, 30, tz='Europe/Zurich')
    monkeypatch.setattr(DateTimeUtils, 'get_local_now', lambda: first_hour_of_july_in_zurich)

    season_start, season_end = get_current_season_dates()

    assert (season_start, season_end) == (datetime(2027, 7, 1), datetime(2028, 6, 30))
