import pandas as pd

import pytz

ZURICH_TIMEZONE = pytz.timezone('Europe/Zurich')


def add_zurich_timezone(local_datetime: pd.Timestamp):
    return local_datetime.tz_localize(ZURICH_TIMEZONE)


def utc_to_zurich_timestamp(utc_datetime: pd.Timestamp):
    result = utc_datetime.astimezone(ZURICH_TIMEZONE)
    return pd.Timestamp(result)

def get_local_now():
    return add_zurich_timezone(pd.Timestamp.now())
