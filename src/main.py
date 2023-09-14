import configparser
import datetime
import logging

import telegram
from telegram.ext import ApplicationBuilder, ContextTypes

from Utils import PathUtils
from NodeHandler import NodeHandler
from Data.DataAccess import DataAccess

from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService
from Services.SchedulingService import SchedulingService

from OneTimeSetup import OneTimeSetup


def initialize_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


def initialize_services(bot: telegram.Bot, api_config: configparser.RawConfigParser):
    _data_access = DataAccess(api_config)
    _telegram_service = TelegramService(bot, api_config)
    _user_state_service = UserStateService(_data_access)
    _admin_service = AdminService(_data_access)
    _ics_service = IcsService(_data_access)
    _scheduling_service = SchedulingService(_data_access, _telegram_service, api_config)
    return _telegram_service, _user_state_service, _admin_service, _ics_service, _data_access, _scheduling_service


async def send_hi(context: ContextTypes.DEFAULT_TYPE):
    await telegram_service.send_maintainer_hi('Bot was restarted')


def use_one_time_setup(data_access: DataAccess):
    one_time_setup = OneTimeSetup(data_access)
    # one_time_setup.add_timekeepings()


def init_job_queue():
    job_queue = application.job_queue
    # TODO 2x uncomment
    # job_queue.run_once(send_hi, 1)
    # job_queue.run_daily(scheduling_service.send_individual_game_reminders, datetime.time(7, 0, 0))

    job_queue.run_once(scheduling_service.send_individual_game_reminders, 1)  # TODO Delete


if __name__ == "__main__":
    initialize_logging()

    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    application = ApplicationBuilder().token(api_config.get('Telegram', 'api_token')).build()

    telegram_service, user_state_service, admin_service, ics_service, data_access, scheduling_service = \
        initialize_services(application.bot, api_config)

    # use_one_time_setup(data_access)

    node_handler = NodeHandler(application.bot, api_config, telegram_service, user_state_service, admin_service,
                               ics_service, data_access)
    application.add_handler(node_handler)

    init_job_queue()

    application.run_polling()
