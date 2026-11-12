import datetime

import pytest
from telegram.ext import ApplicationBuilder

import main
from features.shvsync.ShvSyncService import ShvSyncService
from Utils.DateTimeUtils import ZURICH_TIMEZONE

EXPECTED_ZURICH_TIMES = {
    'sync_all_teams': (6, 30),
    'send_same_day_game_reminder': (7, 0),
    'send_game_summary': (7, 59),
    'send_previous_day_training_reminder': (8, 30),
    'send_individual_game_reminders': (11, 59),
    'send_individual_tke_reminders': (14, 59),
    'send_individual_training_reminders': (17, 59),
    'send_training_summary': (18, 59),
    'send_timekeeping_summary': (18, 59),
}


@pytest.mark.parametrize('day', [datetime.date(2026, 12, 15), datetime.date(2027, 7, 15)],
                         ids=['winter', 'summer'])
def test_daily_jobs_fire_at_the_same_zurich_time_in_winter_and_summer(day, services, data_access):
    application = ApplicationBuilder().token('123:test').build()
    shv_sync_service = ShvSyncService(data_access, services['telegram_service'])

    main.schedule_daily_jobs(application.job_queue, services['scheduling_service'], shv_sync_service)

    start_of_day = ZURICH_TIMEZONE.localize(datetime.datetime.combine(day, datetime.time()))
    fire_times = {job.name: job.job.trigger.get_next_fire_time(None, start_of_day)
                  for job in application.job_queue.jobs()}
    assert fire_times == {
        name: ZURICH_TIMEZONE.localize(datetime.datetime.combine(day, datetime.time(hour, minute)))
        for name, (hour, minute) in EXPECTED_ZURICH_TIMES.items()}
