import firebase_admin
import configparser

from google.cloud.firestore_v1 import FieldFilter

from firebase_admin import firestore

from Enums.AttendanceState import AttendanceState
from Enums.PlayerState import PlayerState
from Exceptions.ObjectNotFoundException import ObjectNotFoundException
from Utils import PathUtils
from databaseEntities.Game import Game
from databaseEntities.Player import Player
from databaseEntities.PlayerToGame import PlayerToGame
from databaseEntities.PlayerToState import PlayerToState
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training


class FirebaseRepository(object):
    def __init__(self, api_config: configparser.RawConfigParser):
        api_config_path = PathUtils.get_secrets_file_path(api_config['Firebase']['credentialsFileName'])
        cred_object = firebase_admin.credentials.Certificate(api_config_path)
        default_app = firebase_admin.initialize_app(cred_object)
        self.db = firestore.client(default_app)

    def get_player(self, telegram_id: int) -> Player | None:
        player_ref = self.db.collection('Players')
        query_ref = player_ref.where(filter=FieldFilter("telegramId", "==", telegram_id))
        res = query_ref.get()
        if len(res) == 1:
            return Player.from_dict(res[0].id, res[0].to_dict())
        raise ObjectNotFoundException

    def get_player_state(self, player: Player) -> PlayerToState | None:
        player_id = player.doc_id
        query_ref = self.db.collection('PlayersToState').where(filter=FieldFilter("playerId", "==", player_id))
        res = query_ref.get()
        if len(res) == 1:
            return PlayerToState.from_dict(res[0].id, res[0].to_dict())
        raise ObjectNotFoundException

    def update_player_state(self, player_to_state: PlayerToState):
        self.db.collection('PlayersToState').document(player_to_state.doc_id).update(
            {'state': int(player_to_state.state)})

    def update_player_state_via_player_id(self, player_to_state: PlayerToState):
        query_ref = self.db.collection('PlayersToState').where(
            filter=FieldFilter("playerId", "==", player_to_state.player_id))
        res = query_ref.get()
        if len(res) == 1:
            updated_player2state = player_to_state.add_document_id(res[0].id)
            self.update_player_state(updated_player2state)
        else:
            return ObjectNotFoundException

    def add_player(self, new_player: Player):
        return self.db.collection('Players').add(new_player.to_dict())

    def add_player_to_state(self, player_to_state: PlayerToState):
        self.db.collection('PlayersToState').add(player_to_state.to_dict())

    def add_game(self, game: Game):
        self.db.collection('Games').add(game.to_dict())

    def add_timekeeping_event(self, timekeeping_event: TimekeepingEvent):
        self.db.collection('Timekeeping').add(timekeeping_event.to_dict())

    def add_training(self, training: Training):
        self.db.collection('Trainings').add(training.to_dict())

    def print_documents(self, collection: str):
        emp_ref = self.db.collection(collection)
        docs = emp_ref.stream()

        for doc in docs:
            print('{} => {} '.format(doc.id, doc.to_dict()))

