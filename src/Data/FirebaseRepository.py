import firebase_admin
import configparser

from google.cloud.firestore_v1 import FieldFilter

from firebase_admin import firestore

from Utils import PathUtils
from databaseEntities.Game import Game

from Data.Tables import Tables
from Enums.Table import Table

from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.UsersToState import UsersToState

from Utils.CustomExceptions import ObjectNotFoundException, MoreThanOneObjectFoundException


class FirebaseRepository(object):
    def __init__(self, api_config: configparser.RawConfigParser, tables: Tables):
        self.tables = tables
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

    def get_user(self, telegram_id: int) -> TelegramUser | None:
        user_ref = self.db.collection(self.tables.get(Table.USERS_TABLE))
        query_ref = user_ref.where(filter=FieldFilter("telegramId", "==", telegram_id))
        res = query_ref.get()
        if len(res) == 0:
            raise ObjectNotFoundException
        if len(res) == 1:
            return TelegramUser.from_dict(res[0].id, res[0].to_dict())
        else:
            raise MoreThanOneObjectFoundException

    def get_user_state(self, user: TelegramUser) -> UsersToState | None:
        user_id = user.doc_id
        query_ref = self.db.collection(self.tables.get(Table.USERS_TO_STATE_TABLE)).where(filter=FieldFilter("userId", "==", user_id))
        res = query_ref.get()
        if len(res) == 1:
            return UsersToState.from_dict(res[0].id, res[0].to_dict())
        raise ObjectNotFoundException

    def get_game(self, doc_id: str) -> Game | None:
        self.raise_exception_if_document_not_exists(self.tables.get(Table.GAMES_TABLE), doc_id)
        query_ref = self.db.collection(self.tables.get(Table.GAMES_TABLE)).document(doc_id)
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

    def update_user_state(self, user_to_state: UsersToState):
        self.raise_exception_if_document_not_exists(self.tables.get(Table.USERS_TO_STATE_TABLE), user_to_state.doc_id)
        self.db.collection(self.tables.get(Table.USERS_TO_STATE_TABLE)).document(user_to_state.doc_id).update(
            {'state': int(user_to_state.state)})

    def update_user_state_via_user_id(self, user_to_state: UsersToState):
        query_ref = self.db.collection(self.tables.get(Table.USERS_TO_STATE_TABLE)).where(
            filter=FieldFilter("userId", "==", user_to_state.user_id))
        res = query_ref.get()
        if len(res) == 1:
            updated_user_to_state = user_to_state.add_document_id(res[0].id)
            self.update_user_state(updated_user_to_state)
        else:
            return ObjectNotFoundException

    def update_user_via_telegram_id(self, user: TelegramUser):
        user_id = self.get_user(user.telegramId).doc_id
        user.doc_id = user_id
        self.update(user, self.tables.get(Table.USERS_TABLE))

    ########
    # ELSE #
    ########

    def print_documents(self, collection: str):
        emp_ref = self.db.collection(collection)
        docs = emp_ref.stream()

        for doc in docs:
            print('{} => {} '.format(doc.id, doc.to_dict()))
