import firebase_admin
import configparser

from google.cloud.firestore_v1 import FieldFilter

from firebase_admin import firestore

from src.States.AttendanceState import AttendanceState
from src.States.PlayerState import PlayerState
from src.Utils import PathUtils
from src.databaseEntities.Game import Game
from src.databaseEntities.Player import Player
from src.databaseEntities.PlayerToGame import PlayerToGame
from src.databaseEntities.PlayerToState import PlayerToState
from src.databaseEntities.TimekeepingEvent import TimekeepingEvent
from src.databaseEntities.Training import Training


class FirebaseRepository(object):
    def __init__(self, api_config: configparser.RawConfigParser):
        api_config_path = PathUtils.get_secrets_file_path(api_config['Firebase']['credentialsFileName'])
        cred_object = firebase_admin.credentials.Certificate(api_config_path)
        default_app = firebase_admin.initialize_app(cred_object)
        self.db = firestore.client(default_app)

    def get_documents(self, collection: str):

        emp_ref = self.db.collection(collection)
        docs = emp_ref.stream()

        for doc in docs:
            print('{} => {} '.format(doc.id, doc.to_dict()))

    def get_player(self, telegram_id: int):
        player_ref = self.db.collection('Players')
        query_ref = player_ref.where(filter=FieldFilter("telegramId", "==", telegram_id))
        res = query_ref.get()
        if len(res) == 1:
            return res[0]
        return -42

    def get_player_object(self, telegram_id: int):
        player_ref = self.db.collection('Players')
        query_ref = player_ref.where(filter=FieldFilter("telegramId", "==", telegram_id))
        res = query_ref.get()
        if len(res) == 1:
            return Player.from_dict(res[0].to_dict())
        return -42

    def get_player_state(self, telegram_id: int):
        player_id = self.get_player(telegram_id).id
        query_ref = self.db.collection('PlayersToState').where(filter=FieldFilter("playerId", "==", player_id))
        return PlayerToState.from_dict(query_ref.get()[0].to_dict())

    def update_player_state(self, player_firebase_id: str, new_player_state: PlayerState):
        # TODO doc_ref_id = self.
        # self.db.collection('PlayersToState').document(doc_ref_id).update({'state': int(new_player_state)})
        pass

    def add_player(self, new_player: Player):
        return self.db.collection('Players').add(new_player.to_dict())

    def add_player_to_state(self, player_to_state: PlayerToState):
        self.db.collection('PlayersToState').add(player_to_state.to_dict())

    def get_player_id_from_telegram_id(self, telegram_id: int):
        return self.get_player(telegram_id).id

    def add_game(self, game: Game):
        self.db.collection('Games').add(game.to_dict())

    def add_timekeeping_event(self, timekeeping_event: TimekeepingEvent):
        self.db.collection('Timekeeping').add(timekeeping_event.to_dict())

    def add_training(self, training: Training):
        self.db.collection('Trainings').add(training.to_dict())

    def add_player_to_game(self, player_to_game: PlayerToGame):
        self.db.collection('PlayersToGames').add(player_to_game.to_dict())

    def get_player_to_state_document(self, player_fb_id):
        pass
# return document in playerToState
