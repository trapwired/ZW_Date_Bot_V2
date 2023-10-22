import datetime

import pytz


ZURICH_TIMEZONE = pytz.timezone('Europe/Zurich')


def add_zurich_timezone(local_datetime: datetime):
     return ZURICH_TIMEZONE.localize(local_datetime)


def utc_to_zurich_timestamp(utc_datetime: datetime):
    return utc_datetime.astimezone(ZURICH_TIMEZONE)
