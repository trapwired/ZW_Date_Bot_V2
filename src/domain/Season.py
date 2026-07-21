"""Season boundaries (July 1 - June 30): domain rule shared by every storage
backend for season-scoped queries (player metrics, relevant events)."""
from datetime import datetime


def get_current_season_dates():
    today = datetime.today()
    current_year = today.year

    if today.month < 7:
        # Current season started last year on July 1st
        season_start = datetime(current_year - 1, 7, 1)
        season_end = datetime(current_year, 6, 30)
    else:
        season_start = datetime(current_year, 7, 1)
        season_end = datetime(current_year + 1, 6, 30)

    return season_start, season_end
