import datetime
import logging

import telegram
from telegram.ext import ApplicationBuilder, ContextTypes

from Utils.ApiConfig import ApiConfig

from NodeHandler import NodeHandler
from Data.DataAccess import DataAccess

from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService
from Services.SchedulingService import SchedulingService
from Services.TriggerService import TriggerService

from OneTimeSetup import OneTimeSetup


def initialize_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


def initialize_services(bot: telegram.Bot, api_config: ApiConfig):
    _data_access = DataAccess(api_config)
    _telegram_service = TelegramService(bot, api_config)
    _user_state_service = UserStateService(_data_access)
    _admin_service = AdminService(_data_access)
    _ics_service = IcsService(_data_access)
    _scheduling_service = SchedulingService(_data_access, _telegram_service, api_config)
    _trigger_service = TriggerService(_data_access, _telegram_service)
    return _telegram_service, _user_state_service, _admin_service, _ics_service, _data_access, _scheduling_service, _trigger_service


async def send_hi(context: ContextTypes.DEFAULT_TYPE):
    await telegram_service.send_maintainer_hi('Bot was restarted')


def use_one_time_setup(data_access: DataAccess):
    one_time_setup = OneTimeSetup(data_access)
    # one_time_setup.add_timekeepings()


def run_job_queue():
    job_queue = application.job_queue
    job_queue.run_once(send_hi, 1)

    # Individual event reminders
    job_queue.run_daily(  # Game Reminders, each day at 11:59 local time
        scheduling_service.send_individual_game_reminders,
        datetime.time(9, 59, 0))

    job_queue.run_daily(  # Training Reminders, each day at 17:59 local time
        scheduling_service.send_individual_training_reminders,
        datetime.time(15, 59, 0))

    job_queue.run_daily(  # TKE Reminders, each day at 14:59 local time
        scheduling_service.send_individual_tke_reminders,
        datetime.time(12, 59, 0))

    # Summary to trainers / organisators
    job_queue.run_daily(  # Game summaries, each day at 7:59 local time
        scheduling_service.send_game_summary,
        datetime.time(5, 59, 0))

    job_queue.run_daily(  # Training summaries, each day at 18:59 local time
        scheduling_service.send_training_summary,
        datetime.time(16, 59, 0))

    job_queue.run_daily(  # Timekeeping summaries, each day at 18:59 local time
        scheduling_service.send_timekeeping_summary,
        datetime.time(16, 59, 0))


if __name__ == "__main__":
    initialize_logging()

    api_config = ApiConfig()

    application = ApplicationBuilder().token(api_config.get_key('Telegram', 'api_token')).build()

    telegram_service, user_state_service, admin_service, ics_service, data_access, scheduling_service, trigger_service \
        = initialize_services(application.bot, api_config)

    # use_one_time_setup(data_access)

    node_handler = NodeHandler(application.bot, api_config, telegram_service, user_state_service, admin_service,
                               ics_service, data_access, trigger_service)
    application.add_handler(node_handler)

    run_job_queue()

    application.run_polling()
