import configparser
import os

from src import PathUtils
from src.FirebaseHandler import FirebaseHandler
from src.PlayerState import PlayerState
from src.firestoreEntities.Player import Player


def db_tests(firebaseHandler):
    print(firebaseHandler.get_player_state(42))
    p = Player(43, 'hanna', 'lastname', PlayerState.INIT)
    firebaseHandler.add_player(p)
    firebaseHandler.update_player_state(42, PlayerState.INIT)


if __name__ == "__main__":
    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    firebaseHandler = FirebaseHandler(api_config)

