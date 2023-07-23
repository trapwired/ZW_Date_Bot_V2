import configparser
import datetime
import os

from src import PathUtils
from src.FirebaseHandler import FirebaseHandler
from src.PlayerState import PlayerState
from src.firestoreEntities.Game import Game
from src.firestoreEntities.Player import Player
from src.firestoreEntities.TimekeepingEvent import TimekeepingEvent
from src.firestoreEntities.Training import Training


def db_examples(firebase_handler):
    # See / Update Player State
    print(firebase_handler.get_player_state(42))
    firebase_handler.update_player_state(42, PlayerState.INIT)

    # Add Player
    p = Player(43, 'domi', 'lastname', PlayerState.INIT)
    firebase_handler.add_player(p)

    # Add Game
    game = Game(datetime.datetime.now(), "Zürich Utogrund", "Testgegner")
    firebase_handler.add_game(game)

    # Add timekeepingEvent
    tke = TimekeepingEvent(datetime.datetime.now(), "Zürich Saalsporthalle", 42)
    firebase_handler.add_timekeeping_event(tke)

    # Add Training
    training = Training(datetime.datetime.now(), "Zürich Utogrund")
    firebase_handler.add_training(training)


if __name__ == "__main__":
    api_config = configparser.RawConfigParser()
    api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')

    firebase_handler = FirebaseHandler(api_config)
