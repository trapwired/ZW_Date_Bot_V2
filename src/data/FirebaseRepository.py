from datetime import datetime
from multipledispatch import dispatch

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from data.Tables import Tables

from Enums.Table import Table
from Enums.Role import Role
from Enums.RoleSet import RoleSet
from Enums.Event import Event

from domain.entities.DatabaseEntity import DatabaseEntity
from domain.entities.Game import Game
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training
from domain.entities.Attendance import Attendance
from domain.entities.PlayerMetric import PlayerMetric
from domain.entities.TempData import TempData
from domain.entities.Settings import Settings

from Utils.CustomExceptions import ObjectNotFoundException, MoreThanOneObjectFoundException, \
    NoTempDataFoundException, TooManyObjectsFoundException
from Utils import PathUtils
from Utils.ApiConfig import ApiConfig
from Utils import DateTimeUtils


def get_current_season_dates():
    today = datetime.today()
    current_year = today.year

    # Determine if we are in the first half of the year (January to June)
    if today.month < 7:
        # Current season started last year on July 1st
        season_start = datetime(current_year - 1, 7, 1)
        season_end = datetime(current_year, 6, 30)
    else:
        # Current season started this year on July 1st
        season_start = datetime(current_year, 7, 1)
        season_end = datetime(current_year + 1, 6, 30)

    return season_start, season_end


class FirebaseRepository(object):
    # The settings table holds a single configuration document under a fixed id, so it can be
    # read/written deterministically without a query (no "more than one" ambiguity).
    SETTINGS_DOC_ID = 'config'

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
        season_start, season_end = get_current_season_dates()
        query_ref = (self.db.collection(self.tables.get(Table.PLAYER_METRIC))
            .where(filter=FieldFilter("userId", "==", user.doc_id))) \
            .where(filter=FieldFilter("insertTimestamp", ">", season_start)) \
            .where(filter=FieldFilter("insertTimestamp", "<", season_end))
        entries = query_ref.get()
        if len(entries) == 1:
            return PlayerMetric.from_dict(entries[0].id, entries[0].to_dict())
        if len(entries) > 1:
            # A player should only ever have one metric per season; if a race created duplicates,
            # self-heal by collapsing to a single record (the query has no ordering, so which one
            # survives is arbitrary) so later reads aren't ambiguous.
            for entry in entries[1:]:
                self.db.collection(self.tables.get(Table.PLAYER_METRIC)).document(entry.id).delete()
            return PlayerMetric.from_dict(entries[0].id, entries[0].to_dict())
        new_player_metric = PlayerMetric(user.doc_id, 0, 0, 0, DateTimeUtils.get_local_now())
        doc_ref = self.add(new_player_metric, Table.PLAYER_METRIC)
        return new_player_metric.add_document_id(doc_ref[1].id)

    def get_temp_data(self, user_doc_id: str) -> TempData:
        query_ref = (self.db.collection(self.tables.get(Table.TEMP_DATA_TABLE))
                     .where(filter=FieldFilter("userDocId", "==", user_doc_id)))
        result_list = query_ref.get()
        if len(result_list) == 0:
            raise NoTempDataFoundException()
        if len(result_list) > 1:
            raise TooManyObjectsFoundException()
        temp_data = result_list[0]
        return TempData.from_dict(temp_data.id, temp_data.to_dict())

    def get_settings(self) -> Settings | None:
        collection = self.tables.get(Table.SETTINGS_TABLE)
        doc = self.db.collection(collection).document(self.SETTINGS_DOC_ID).get()
        if not doc.exists:
            return None
        return Settings.from_dict(doc.id, doc.to_dict())

    def set_settings(self, settings: Settings):
        # Upsert: creates the single settings document on first save, overwrites it afterwards.
        collection = self.tables.get(Table.SETTINGS_TABLE)
        self.db.collection(collection).document(self.SETTINGS_DOC_ID).set(settings.to_dict())

    def get_future_events(self, table: Table) -> list:
        # get all events in table which take place in the future
        now = datetime.now()
        query_ref = (self.db.collection(self.tables.get(table))
                     .where(filter=FieldFilter("timestamp", ">", now)))
        event_list = query_ref.get()
        if len(event_list) == 0:
            return []
        return event_list

    def get_attendance_list(self, doc_id: str, table: Table):
        query_ref = (self.db.collection(self.tables.get(table))
                     .where(filter=FieldFilter("eventId", "==", doc_id)))
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
        table = self.get_event_attendance_table(event_type)
        query_ref = self.db.collection(table).where(filter=FieldFilter("userId", "==", user.doc_id))
        entries = query_ref.get()
        return entries

    # Firestore caps the 'in' operator at 30 comparison values, so batch the ids.
    FIRESTORE_IN_LIMIT = 30

    def get_all_event_attendances(self, event_type: Event, relevant_doc_ids: list[str]):
        if len(relevant_doc_ids) == 0:
            return []
        table = self.get_event_attendance_table(event_type)
        entries = []
        for i in range(0, len(relevant_doc_ids), self.FIRESTORE_IN_LIMIT):
            batch = relevant_doc_ids[i:i + self.FIRESTORE_IN_LIMIT]
            query_ref = self.db.collection(table).where(filter=FieldFilter("eventId", "in", batch))
            entries.extend(query_ref.get())
        return entries

    def get_all_relevant_event_ids(self, event_type: Event):
        table = self.get_event_table(event_type)
        season_start, _ = get_current_season_dates()
        query_ref = (self.db.collection(table)) \
            .where(filter=FieldFilter("timestamp", ">", season_start)) \
            .where(filter=FieldFilter("timestamp", "<", DateTimeUtils.get_local_now()))
        # filter > start date and < end date
        entries = query_ref.get()
        result = []
        for row in entries:
            result.append(row.id)
        return result

    def get_all_player_metrics(self):
        table = self.tables.get(Table.PLAYER_METRIC)
        season_start, season_end = get_current_season_dates()
        query_ref = (self.db.collection(table)) \
            .where(filter=FieldFilter("insertTimestamp", ">", season_start)) \
            .where(filter=FieldFilter("insertTimestamp", "<", season_end))
        entries = query_ref.get()
        return entries

    def get_users_to_state_by_role(self, role: Role):
        query_ref = self.db.collection(self.tables.get(Table.USERS_TO_STATE_TABLE)).where(
            filter=FieldFilter("role", "==", role))
        return query_ref.get()

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
            return ObjectNotFoundException(collection, user_to_state.user_id)

    def update_user_via_telegram_id(self, user: TelegramUser):
        user_id = self.get_user(user.telegramId).doc_id
        user.doc_id = user_id
        self.update(user, self.tables.get(Table.USERS_TABLE))

    ##########
    # DELETE #
    ##########

    @dispatch(TempData)
    def delete(self, temp_data: TempData):
        db_table = self.tables.get(Table.TEMP_DATA_TABLE)
        self.db.collection(db_table).document(temp_data.doc_id).delete()

    def delete_game(self, doc_id: str):
        db_table = self.tables.get(Table.GAMES_TABLE)
        self.db.collection(db_table).document(doc_id).delete()

    def delete_training(self, doc_id: str):
        db_table = self.tables.get(Table.TRAININGS_TABLE)
        self.db.collection(db_table).document(doc_id).delete()

    def delete_timekeeping(self, doc_id: str):
        db_table = self.tables.get(Table.TIMEKEEPING_TABLE)
        self.db.collection(db_table).document(doc_id).delete()

    def delete_event_attendances(self, event_type: Event, event_doc_id: str):
        table = self.get_event_attendance_table(event_type)
        query_ref = self.db.collection(table) \
            .where(filter=FieldFilter("eventId", "==", event_doc_id))
        self._delete_documents(table, query_ref.stream())

    def delete_all_player_metrics(self) -> int:
        db_table = self.tables.get(Table.PLAYER_METRIC)
        return self._delete_documents(db_table, self.db.collection(db_table).stream())

    def _delete_documents(self, table: str, docs) -> int:
        deleted_count = 0
        for doc in docs:
            self.db.collection(table).document(doc.id).delete()
            deleted_count += 1
        return deleted_count



    ########
    # ELSE #
    ########

    def print_documents(self, collection: str):
        emp_ref = self.db.collection(collection)
        docs = emp_ref.stream()

        for doc in docs:
            print('{} => {} '.format(doc.id, doc.to_dict()))

    def get_event_attendance_table(self, event_type: Event):
        match event_type:
            case Event.GAME:
                return self.tables.get(Table.GAME_ATTENDANCE_TABLE)
            case Event.TRAINING:
                return self.tables.get(Table.TRAINING_ATTENDANCE_TABLE)
            case Event.TIMEKEEPING:
                return self.tables.get(Table.TIMEKEEPING_ATTENDANCE_TABLE)

    def get_event_table(self, event_type: Event):
        match event_type:
            case Event.GAME:
                return self.tables.get(Table.GAMES_TABLE)
            case Event.TRAINING:
                return self.tables.get(Table.TRAININGS_TABLE)
            case Event.TIMEKEEPING:
                return self.tables.get(Table.TIMEKEEPING_TABLE)

    def reset_all_player_event_attendance(self, doc_id: str, table: Table):
        collection_reference = self.db.collection(self.tables.get(table))
        attendance_rows = collection_reference.where(filter=FieldFilter("eventId", "==", doc_id)).get()
        field_update = {"state": 0}
        for row in attendance_rows:
            doc = collection_reference.document(row.id)
            doc.update(field_update)

