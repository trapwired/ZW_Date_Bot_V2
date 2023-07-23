import firebase_admin
import configparser

from google.cloud.firestore_v1 import FieldFilter

import PathUtils
from firebase_admin import firestore

from src.PlayerState import PlayerState
from src.firestoreEntities.Player import Player


class FirebaseHandler(object):
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
        return PlayerState(self.get_player_object(telegram_id).state)

    def update_player_state(self, telegram_id: int, new_player_state: PlayerState):
        player_id = self.get_player(telegram_id).id
        self.db.collection('Players').document(player_id).update({'state': int(new_player_state)})

    def add_player(self, new_player: Player):
        self.db.collection('Players').add(new_player.to_dict())


