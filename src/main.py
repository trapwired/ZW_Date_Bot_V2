import configparser

from src import PathUtils
from src.FirebaseService import FirebaseService
from src.firestoreEntities.PlayerToGame import PlayerToGame

if __name__ == "__main__":
    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    firebase_service = FirebaseService(api_config)

    # TODO try out add_player (via service)

    # TODO WIP Add PlayerToGame from telegramId --> add to service
    # player_id = firebase_handler.get_player_id_from_telegram_id(42)
    # ptog = PlayerToGame(pl)
