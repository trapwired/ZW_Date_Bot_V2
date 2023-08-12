import configparser
from multipledispatch import dispatch

from Data.FirebaseRepository import FirebaseRepository
from Data.Tables import Tables

from Enums.UserState import UserState
from Enums.Table import Table

from databaseEntities.Game import Game
from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.UsersToState import UsersToState
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.GameAttendance import GameAttendance
from databaseEntities.TimeKeepingAttendance import TimeKeepingAttendance
from databaseEntities.TrainingAttendance import TrainingAttendance
from databaseEntities.Training import Training

from Exceptions.DocumentIdNotPresentException import DocumentIdNotPresentException

from src.Enums.UserState import UserState


class DataAccess(object):

    def __init__(self, api_config: configparser.RawConfigParser):
        self.tables = Tables(api_config)
        self.firebase_repository = FirebaseRepository(api_config, self.tables)

    #######
    # ADD #
    #######

    @dispatch(TelegramUser)
    def add(self, user: TelegramUser) -> UsersToState:
        doc_ref = self.firebase_repository.add(user, self.tables.get(Table.USERS_TABLE))
        user_doc_id = doc_ref[1].id
        user_to_state = UsersToState(user_doc_id, UserState.INIT)
        doc_id = self.firebase_repository.add(user_to_state, self.tables.get(Table.USERS_TO_STATE_TABLE))
        return user_to_state.add_document_id(doc_id[1].id)

    @dispatch(Game)
    def add(self, game: Game) -> Game:
        doc_ref = self.firebase_repository.add(game, self.tables.get(Table.GAMES_TABLE))
        return game.add_document_id(doc_ref[1].id)

    @dispatch(Training)
    def add(self, training: Training) -> Training:
        doc_ref = self.firebase_repository.add(training, self.tables.get(Table.TRAININGS_TABLE))
        return training.add_document_id(doc_ref[1].id)

    @dispatch(TimekeepingEvent)
    def add(self, timekeeping_event: TimekeepingEvent) -> TimekeepingEvent:
        doc_ref = self.firebase_repository.add(timekeeping_event, self.tables.get(Table.TIMEKEEPING_TABLE))
        return timekeeping_event.add_document_id(doc_ref[1].id)

    @dispatch(GameAttendance)
    def add(self, game_attendance: GameAttendance) -> GameAttendance:
        doc_ref = self.firebase_repository.add(game_attendance, self.tables.get(Table.GAME_ATTENDANCE_TABLE))
        return game_attendance.add_document_id(doc_ref[1].id)

    @dispatch(TrainingAttendance)
    def add(self, training_attendance: TrainingAttendance) -> TrainingAttendance:
        doc_ref = self.firebase_repository.add(training_attendance, self.tables.get(Table.TRAINING_ATTENDANCE_TABLE))
        return training_attendance.add_document_id(doc_ref[1].id)

    @dispatch(TimeKeepingAttendance)
    def add(self, timekeeping_attendance: TimeKeepingAttendance) -> TimeKeepingAttendance:
        doc_ref = self.firebase_repository.add(timekeeping_attendance,
                                               self.tables.get(Table.TIMEKEEPING_ATTENDANCE_TABLE))
        return timekeeping_attendance.add_document_id(doc_ref[1].id)

    ##########
    # UPDATE #
    ##########

    @dispatch(UsersToState)
    def update(self, users_to_state: UsersToState):
        if users_to_state.doc_id is None:
            self.firebase_repository.update_user_state_via_user_id(users_to_state)
        else:
            self.firebase_repository.update(users_to_state, self.tables.get(Table.USERS_TO_STATE_TABLE))

    @dispatch(TelegramUser)
    def update(self, user: TelegramUser):
        if user.doc_id is None:
            self.firebase_repository.update_user_via_telegram_id(user)
        else:
            self.firebase_repository.update(user, self.tables.get(Table.USERS_TABLE))

    @dispatch(Game)
    def update(self, game: Game):
        if game.doc_id is None:
            # TODO: Find / Match / AddDocId
            raise DocumentIdNotPresentException()
        self.firebase_repository.update(game, self.tables.get(Table.GAMES_TABLE))

    @dispatch(Training)
    def update(self, training: Training):
        if training.doc_id is None:
            # TODO: Find / Match / AddDocId
            raise DocumentIdNotPresentException()
        self.firebase_repository.update(training, self.tables.get(Table.TRAININGS_TABLE))

    @dispatch(TimekeepingEvent)
    def update(self, timekeeping_event: TimekeepingEvent):
        if timekeeping_event.doc_id is None:
            # TODO: Find / Match / AddDocId
            raise DocumentIdNotPresentException()
        self.firebase_repository.update(timekeeping_event, self.tables.get(Table.TIMEKEEPING_TABLE))

    @dispatch(GameAttendance)
    def update(self, game_attendance: GameAttendance):
        if game_attendance.doc_id is None:
            # TODO / AddDocId
            raise DocumentIdNotPresentException()
        self.firebase_repository.update_game(game_attendance, self.tables.get(Table.GAME_ATTENDANCE_TABLE))

    @dispatch(TrainingAttendance)
    def update(self, training_attendance: TrainingAttendance):
        if training_attendance.doc_id is None:
            # TODO: Find / Match
            raise DocumentIdNotPresentException()
        self.firebase_repository.update(training_attendance, self.tables.get(Table.TRAINING_ATTENDANCE_TABLE))

    @dispatch(TimeKeepingAttendance)
    def update(self, timekeeping_attendance: TimeKeepingAttendance):
        if timekeeping_attendance.doc_id is None:
            # TODO: Find / Match
            raise DocumentIdNotPresentException()
        self.firebase_repository.update(timekeeping_attendance, self.tables.get(Table.TIMEKEEPING_ATTENDANCE_TABLE))

    #######
    # GET #
    #######

    def get_user_state(self, telegram_id: int) -> UsersToState:
        user = self.firebase_repository.get_user(telegram_id)
        return self.firebase_repository.get_user_state(user)
