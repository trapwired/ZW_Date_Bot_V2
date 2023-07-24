import configparser

from src import PathUtils
from src.FirebaseService import FirebaseService
from src.States.AttendanceState import AttendanceState
from src.States.PlayerState import PlayerState
from src.firestoreEntities.Player import Player

if __name__ == "__main__":
    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    firebase_service = FirebaseService(api_config)
    # firebase_service.update_player_to_game_state(telegram_id=42, new_state=AttendanceState.YES)
    # TODO firebase_service.update_player_state(42, PlayerState.NEW)
    # firebase_service.add(Player(43, 'goodbye', 'world'))

    # firebase_service.add_player(42, 'hello', 'world')

    # TODO WIP Add PlayerToGame from telegramId --> add to service
    # player_id = firebase_handler.get_player_id_from_telegram_id(42)
    # ptog = PlayerToGame(pl)