import configparser
import logging
import asyncio

import telegram
from telegram.ext import ApplicationBuilder

from Utils import PathUtils
from NodeHandler import NodeHandler
from Data.DataAccess import DataAccess

from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService


def initialize_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


def initialize_services(bot: telegram.Bot, api_config: configparser.RawConfigParser):
    data_access = DataAccess(api_config)
    telegram_service = TelegramService(bot, api_config)
    user_state_service = UserStateService(data_access)
    admin_service = AdminService(data_access)
    ics_service = IcsService(data_access)
    return telegram_service, user_state_service, admin_service, ics_service, data_access


async def send_hi(telegram_service):
    await telegram_service.send_maintainer_hi('Bot was restarted')


if __name__ == "__main__":
    initialize_logging()

    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    application = ApplicationBuilder().token(api_config.get('Telegram', 'api_token')).build()

    telegram_service, user_state_service, admin_service, ics_service, data_access = initialize_services(application.bot,
                                                                                                        api_config)

    node_handler = NodeHandler(application.bot, api_config, telegram_service, user_state_service, admin_service,
                               ics_service, data_access)
    application.add_handler(node_handler)

    application.run_polling()

    application.job_queue.run_once(send_hi, 0.0)
