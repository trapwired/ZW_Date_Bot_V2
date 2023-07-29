import configparser
import logging
from telegram.ext import ApplicationBuilder

from src.CommandHandler import CommandHandler
from src.Utils import PathUtils


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

    command_handler = CommandHandler(application.bot)
    application.add_handler(command_handler)

    application.run_polling()

    # command handler will init all workflows and services
    # (playerstateservice, adminService)
    # DataAccess
    # (pass down telegram stuff to call in workflows)

    # Init telegram service, give command handler to handle commands

    # firebase_service = FirebaseService(api_config)
    # firebase_service.update_player_to_game_state(telegram_id=42, new_state=AttendanceState.YES)
    # TODO firebase_service.update_player_state(42, PlayerState.NEW)
    # firebase_service.add(Player(43, 'goodbye', 'world'))

    # firebase_service.add_player(42, 'hello', 'world')

    # TODO WIP Add PlayerToGame from telegramId --> add to service
    # player_id = firebase_handler.get_player_id_from_telegram_id(42)
    # ptog = PlayerToGame(pl)
