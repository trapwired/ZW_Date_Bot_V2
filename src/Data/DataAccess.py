import configparser
from multipledispatch import dispatch

from Data.FirebaseRepository import FirebaseRepository
from Enums.PlayerState import PlayerState
from databaseEntities.Game import Game
from databaseEntities.Player import Player
from databaseEntities.PlayerToState import PlayerToState
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.GameAttendance import GameAttendance
from databaseEntities.TimeKeepingAttendance import TimeKeepingAttendance
from databaseEntities.TrainingAttendance import TrainingAttendance
from databaseEntities.Training import Training

from Exceptions.DocumentIdNotPresentException import DocumentIdNotPresentException

from Data.Tables import Tables

from Enums.Table import Table


class DataAccess(object):

    def __init__(self, api_config: configparser.RawConfigParser):
        self.tables = Tables(api_config)
        self.firebase_repository = FirebaseRepository(api_config, self.tables)

    #######
    # ADD #
    #######

    @dispatch(Player)
    def add(self, player: Player) -> PlayerToState:
        doc_ref = self.firebase_repository.add(player, self.tables.get(Table.PLAYERS_TABLE))
        player_doc_id = doc_ref[1].id
        player_to_state = PlayerToState(player_doc_id, PlayerState.INIT)
        doc_id = self.firebase_repository.add(player_to_state, self.tables.get(Table.PLAYERS_TO_STATE_TABLE))
        return player_to_state.add_document_id(doc_id[1].id)

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

    @dispatch(PlayerToState)
    def update(self, player_to_state: PlayerToState):
        if player_to_state.doc_id is None:
            self.firebase_repository.update_player_state_via_player_id(player_to_state)
        else:
            self.firebase_repository.update(player_to_state, self.tables.get(Table.PLAYERS_TO_STATE_TABLE))

    @dispatch(Player)
    def update(self, player: Player):
        if player.doc_id is None:
            self.firebase_repository.update_player_via_telegram_id(player)
        else:
            self.firebase_repository.update(player, self.tables.get(Table.PLAYERS_TABLE))

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

    def get_player_state(self, telegram_id: int) -> PlayerToState:
        player = self.firebase_repository.get_player(telegram_id)
        return self.firebase_repository.get_player_state(player)
