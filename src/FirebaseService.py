import configparser
import datetime

from src.FirebaseAccess import FirebaseAccess
from src.States.PlayerState import PlayerState
from src.firestoreEntities.Game import Game
from src.firestoreEntities.Player import Player
from src.firestoreEntities.PlayerToState import PlayerToState
from src.firestoreEntities.TimekeepingEvent import TimekeepingEvent
from src.firestoreEntities.Training import Training


class FirebaseService(object):
    def __init__(self, api_config: configparser.RawConfigParser):
        self.firebase_access = FirebaseAccess(api_config)

    def db_examples(self):
        # See / Update Player State
        print(self.firebase_access.get_player_state(42))
        self.firebase_access.update_player_state(42, PlayerState.INIT)

        # Add Player
        p = Player(43, 'domi', 'lastname')
        self.firebase_access.add_player(p)

        # Add Game
        game = Game(datetime.datetime.now(), "Zürich Utogrund", "Testgegner")
        self.firebase_access.add_game(game)

        # Add timekeepingEvent
        tke = TimekeepingEvent(datetime.datetime.now(), "Zürich Saalsporthalle", 42)
        self.firebase_access.add_timekeeping_event(tke)

        # Add Training
        training = Training(datetime.datetime.now(), "Zürich Utogrund")
        self.firebase_access.add_training(training)

    # TODO Add retry / error handling logic, call via this method all db_access

    def add_player(self, telegram_id: int, firstname: str, lastname: str):
        new_player = Player(telegram_id, firstname, lastname)
        doc_id = self.firebase_access.add_player(new_player)

        player_to_state = PlayerToState(doc_id, PlayerState.INIT)
        self.firebase_access.add_player_to_state(player_to_state)

    # TODO Add add_game and co

    
        