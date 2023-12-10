import datetime
from multipledispatch import dispatch

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from Data.Tables import Tables

from Enums.Table import Table
from Enums.RoleSet import RoleSet
from Enums.Event import Event

from databaseEntities.DatabaseEntity import DatabaseEntity
from databaseEntities.Game import Game
from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.UsersToState import UsersToState
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training
from databaseEntities.Attendance import Attendance
from databaseEntities.PlayerMetric import PlayerMetric

from Utils.CustomExceptions import ObjectNotFoundException, MoreThanOneObjectFoundException
from Utils import PathUtils
from Utils.ApiConfig import ApiConfig




class FirebaseRepository(object):
    def __init__(self, api_config: ApiConfig, tables: Tables):
        self.tables = tables
        api_config_path = PathUtils.get_secrets_file_path(api_config.get_key('Firebase', 'credentialsFileName'))
        cred_object = firebase_admin.credentials.Certificate(api_config_path)
        default_app = firebase_admin.initialize_app(cred_object)
        self.db = firestore.client(default_app)

    def raise_exception_if_document_not_exists(self, collection: str, document_ref: str):
        doc = self.db.collection(collection).document(document_ref)
        res = doc.get().to_dict()
        if res is None:
            raise ObjectNotFoundException(collection, document_ref)

    #######
    # GET #
    #######

    def get_document(self, doc_id: str, table: Table):
        db_table = self.tables.get(table)
        self.raise_exception_if_document_not_exists(db_table, doc_id)
        query_ref = self.db.collection(db_table).document(doc_id)
        return query_ref.get()

    @dispatch(int)
    def get_user(self, telegram_id: int) -> TelegramUser | None:
        table = self.tables.get(Table.USERS_TABLE)
        user_ref = self.db.collection(table)
        query_ref = user_ref.where(filter=FieldFilter("telegramId", "==", telegram_id))
        res = query_ref.get()
        if len(res) == 0:
            raise ObjectNotFoundException(table, telegram_id)
        if len(res) == 1:
            return TelegramUser.from_dict(res[0].id, res[0].to_dict())
        else:
            raise MoreThanOneObjectFoundException

    @dispatch(str)
    def get_user(self, doc_id: str) -> TelegramUser | None:
        res = self.get_document(doc_id, Table.USERS_TABLE)
        return TelegramUser.from_dict(res.id, res.to_dict())

    def get_user_state(self, user: TelegramUser) -> UsersToState | None:
        user_id = user.doc_id
        collection = self.tables.get(Table.USERS_TO_STATE_TABLE)
        query_ref = self.db.collection(collection).where(
            filter=FieldFilter("userId", "==", user_id))
        res = query_ref.get()
        if len(res) == 1:
            return UsersToState.from_dict(res[0].id, res[0].to_dict())
        raise ObjectNotFoundException(collection, res[0].id)

    def get_game(self, doc_id: str) -> Game | None:
        res = self.get_document(doc_id, Table.GAMES_TABLE)
        return Game.from_dict(res.id, res.to_dict())

    def get_training(self, doc_id: str) -> Training | None:
        res = self.get_document(doc_id, Table.TRAININGS_TABLE)
        return Training.from_dict(res.id, res.to_dict())

    def get_timekeeping(self, doc_id: str) -> TimekeepingEvent | None:
        res = self.get_document(doc_id, Table.TIMEKEEPING_TABLE)
        return TimekeepingEvent.from_dict(res.id, res.to_dict())

    def get_player_metric(self, user: TelegramUser):
        query_ref = self.db.collection(self.tables.get(Table.PLAYER_METRIC)).where(
            filter=FieldFilter("userId", "==", user.doc_id))
        entries = query_ref.get()
        if len(entries) > 0:
            return PlayerMetric.from_dict(entries[0].id, entries[0].to_dict())
        new_player_metric = PlayerMetric(user.doc_id, 0, 0, 0)
        doc_ref = self.add(new_player_metric, Table.PLAYER_METRIC)
        return new_player_metric.add_document_id(doc_ref[1].id)

    def get_future_events(self, table: Table) -> list:
        # get all events in table which take place in the future
        now = datetime.datetime.now()
        query_ref = self.db.collection(self.tables.get(table)).where(filter=FieldFilter("timestamp", ">", now))
        event_list = query_ref.get()
        if len(event_list) == 0:
            return []
        return event_list

    def get_attendance_list(self, doc_id: str, table: Table):
        query_ref = self.db.collection(self.tables.get(table)).where(filter=FieldFilter("eventId", "==", doc_id))
        entries = query_ref.get()
        return entries

    def get_attendance(self, user: TelegramUser, event_doc_id: str, table: Table):
        query_ref = self.db.collection(self.tables.get(table)) \
            .where(filter=FieldFilter("userId", "==", user.doc_id)) \
            .where(filter=FieldFilter("eventId", "==", event_doc_id))
        result = query_ref.get()
        if len(result) == 0:
            raise ObjectNotFoundException(self.tables.get(table), user.doc_id)
        if len(result) > 1:
            raise MoreThanOneObjectFoundException()
        attendance = result[0]
        return Attendance.from_dict(attendance.id, attendance.to_dict())

    def get_all_user_event_attendance(self, user: TelegramUser, event_type: Event):
        table = self.get_event_table(event_type)
        query_ref = self.db.collection(table).where(filter=FieldFilter("userId", "==", user.doc_id))
        entries = query_ref.get()
        return entries

    def get_all_player_metrics(self):
        table = self.tables.get(Table.PLAYER_METRIC)
        query_ref = self.db.collection(table)
        entries = query_ref.get()
        return entries

    def get_all_active_players_to_state(self):
        query_ref = self.db.collection(self.tables.get(Table.USERS_TO_STATE_TABLE)).where(
            filter=FieldFilter("role", "in", RoleSet.ACTIVE_PLAYERS))
        entries = query_ref.get()
        return entries

    def get_event_attendance_doc_id(self, attendance: Attendance, table: Table):
        query_ref = self.db.collection(self.tables.get(table)) \
            .where(filter=FieldFilter("userId", "==", attendance.user_id)) \
            .where(filter=FieldFilter("eventId", "==", attendance.event_id))
        result = query_ref.get()
        if len(result) == 0:
            return None
        if len(result) > 1:
            raise MoreThanOneObjectFoundException(attendance)
        return result[0].id

    ################
    # ADD / UPDATE #
    ################

    @dispatch(DatabaseEntity, Table)
    def add(self, new_object: DatabaseEntity, table: Table):
        collection = self.tables.get(table)
        return self.add(new_object, collection)

    @dispatch(DatabaseEntity, str)
    def add(self, new_object: DatabaseEntity, collection: str):
        return self.db.collection(collection).add(new_object.to_dict())

    @dispatch(DatabaseEntity, Table)
    def update(self, db_object: DatabaseEntity, table: Table):
        collection = self.tables.get(table)
        return self.update(db_object, collection)

    @dispatch(DatabaseEntity, str)
    def update(self, db_object: DatabaseEntity, collection: str):
        self.raise_exception_if_document_not_exists(collection, db_object.doc_id)
        self.db.collection(collection).document(db_object.doc_id).update(db_object.to_dict())
        return db_object

    def update_user_state(self, user_to_state: UsersToState):
        db_table = self.tables.get(Table.USERS_TO_STATE_TABLE)
        self.raise_exception_if_document_not_exists(db_table, user_to_state.doc_id)
        self.db.collection(db_table).document(user_to_state.doc_id).update(
            {'state': int(user_to_state.state)})

    def update_user_state_via_user_id(self, user_to_state: UsersToState):
        collection = self.tables.get(Table.USERS_TO_STATE_TABLE)
        query_ref = self.db.collection(collection).where(
            filter=FieldFilter("userId", "==", user_to_state.user_id))
        res = query_ref.get()
        if len(res) == 1:
            updated_user_to_state = user_to_state.add_document_id(res[0].id)
            self.update_user_state(updated_user_to_state)
        else:
            return ObjectNotFoundException(collection, res[0].id)

    def update_user_via_telegram_id(self, user: TelegramUser):
        user_id = self.get_user(user.telegramId).doc_id
        user.doc_id = user_id
        self.update(user, self.tables.get(Table.USERS_TABLE))

    ##########
    # DELETE #
    ##########

    def delete_game(self, doc_id: str):
        db_table = self.tables.get(Table.GAMES_TABLE)
        self.db.collection(db_table).document(doc_id).delete()

    def delete_training(self, doc_id: str):
        db_table = self.tables.get(Table.TRAININGS_TABLE)
        self.db.collection(db_table).document(doc_id).delete()

    def delete_timekeeping(self, doc_id: str):
        db_table = self.tables.get(Table.TIMEKEEPING_TABLE)
        self.db.collection(db_table).document(doc_id).delete()

    ########
    # ELSE #
    ########

    def print_documents(self, collection: str):
        emp_ref = self.db.collection(collection)
        docs = emp_ref.stream()

        for doc in docs:
            print('{} => {} '.format(doc.id, doc.to_dict()))

    def get_event_table(self, event_type: Event):
        match event_type:
            case Event.GAME:
                return self.tables.get(Table.GAME_ATTENDANCE_TABLE)
            case Event.TRAINING:
                return self.tables.get(Table.TRAINING_ATTENDANCE_TABLE)
            case Event.TIMEKEEPING:
                return self.tables.get(Table.TIMEKEEPING_ATTENDANCE_TABLE)

    def reset_all_player_event_attendance(self, doc_id: str, table: Table):
        collection_reference = self.db.collection(self.tables.get(table))
        attendance_rows = collection_reference.where(filter=FieldFilter("eventId", "==", doc_id)).get()
        field_update = {"state": 0}
        for row in attendance_rows:
            doc = collection_reference.document(row.id)
            doc.update(field_update)

