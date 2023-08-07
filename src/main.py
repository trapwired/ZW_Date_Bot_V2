import configparser
import logging
from telegram.ext import ApplicationBuilder

from CommandHandler import CommandHandler
from Utils import PathUtils
from NodeHandler import NodeHandler


def initialize_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


if __name__ == "__main__":
    initialize_logging()

    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    application = ApplicationBuilder().token(api_config.get('Telegram', 'api_token')).build()

    # command_handler = CommandHandler(application.bot, api_config)
    node_handler = NodeHandler(application.bot, api_config)
    application.add_handler(node_handler)

    application.run_polling()
