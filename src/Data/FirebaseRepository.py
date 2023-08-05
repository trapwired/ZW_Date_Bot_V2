import firebase_admin
import configparser

from google.cloud.firestore_v1 import FieldFilter

from firebase_admin import firestore

from Exceptions.ObjectNotFoundException import ObjectNotFoundException
from Utils import PathUtils
from databaseEntities.Game import Game
from databaseEntities.Player import Player
from databaseEntities.PlayerToState import PlayerToState

GAME_ATTENDANCE_TABLE = 'GameAttendance'
GAMES_TABLE = 'Games'
PLAYERS_TABLE = 'Players'
PLAYERS_TO_STATE_TABLE = 'PlayersToState'
TIMEKEEPING_ATTENDANCE_TABLE = 'TimekeepingAttendance'
TIMEKEEPING_TABLE = 'Timekeeping'
TRAINING_ATTENDANCE_TABLE = 'TrainingAttendance'
TRAININGS_TABLE = 'Trainings'


class FirebaseRepository(object):
    def __init__(self, api_config: configparser.RawConfigParser):
        api_config_path = PathUtils.get_secrets_file_path(api_config['Firebase']['credentialsFileName'])
        cred_object = firebase_admin.credentials.Certificate(api_config_path)
        default_app = firebase_admin.initialize_app(cred_object)
        self.db = firestore.client(default_app)

    def raise_exception_if_document_not_exists(self, collection: str, document_ref: str):
        doc = self.db.collection(collection).document(document_ref)
        res = doc.get().to_dict()
        if res is None:
            raise ObjectNotFoundException

    #######
    # GET #
    #######

    def get_player(self, telegram_id: int) -> Player | None:
        player_ref = self.db.collection(PLAYERS_TABLE)
        query_ref = player_ref.where(filter=FieldFilter("telegramId", "==", telegram_id))
        res = query_ref.get()
        if len(res) == 1:
            return Player.from_dict(res[0].id, res[0].to_dict())
        raise ObjectNotFoundException

    def get_player_state(self, player: Player) -> PlayerToState | None:
        player_id = player.doc_id
        query_ref = self.db.collection(PLAYERS_TO_STATE_TABLE).where(filter=FieldFilter("playerId", "==", player_id))
        res = query_ref.get()
        if len(res) == 1:
            return PlayerToState.from_dict(res[0].id, res[0].to_dict())
        raise ObjectNotFoundException

    def get_game(self, doc_id: str) -> Game | None:
        self.raise_exception_if_document_not_exists(GAMES_TABLE, doc_id)
        query_ref = self.db.collection(GAMES_TABLE).document(doc_id)
        res = query_ref.get()
        return Game.from_dict(res.id, res.to_dict())

    ################
    # ADD / UPDATE #
    ################

    def add(self, new_object, collection: str):
        return self.db.collection(collection).add(new_object.to_dict())

    def update(self, db_object, collection: str):
        self.raise_exception_if_document_not_exists(collection, db_object.doc_id)
        self.db.collection(collection).document(db_object.doc_id).update(db_object.to_dict())

    def update_player_state(self, player_to_state: PlayerToState):
        self.raise_exception_if_document_not_exists(PLAYERS_TO_STATE_TABLE, player_to_state.doc_id)
        self.db.collection(PLAYERS_TO_STATE_TABLE).document(player_to_state.doc_id).update(
            {'state': int(player_to_state.state)})

    def update_player_state_via_player_id(self, player_to_state: PlayerToState):
        query_ref = self.db.collection(PLAYERS_TO_STATE_TABLE).where(
            filter=FieldFilter("playerId", "==", player_to_state.player_id))
        res = query_ref.get()
        if len(res) == 1:
            updated_player2state = player_to_state.add_document_id(res[0].id)
            self.update_player_state(updated_player2state)
        else:
            return ObjectNotFoundException

    def update_player_via_telegram_id(self, player: Player):
        player_id = self.get_player(player.telegramId).doc_id
        player.doc_id = player_id
        self.update(player, PLAYERS_TABLE)

    ########
    # ELSE #
    ########

    def print_documents(self, collection: str):
        emp_ref = self.db.collection(collection)
        docs = emp_ref.stream()

        for doc in docs:
            print('{} => {} '.format(doc.id, doc.to_dict()))
