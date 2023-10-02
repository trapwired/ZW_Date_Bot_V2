import configparser
from multipledispatch import dispatch

from Data.FirebaseRepository import FirebaseRepository
from Data.Tables import Tables

from Enums.UserState import UserState
from Enums.Table import Table
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from databaseEntities.Game import Game
from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.UsersToState import UsersToState
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training
from databaseEntities.Attendance import Attendance

from Utils.CustomExceptions import ObjectNotFoundException, DocumentIdNotPresentException, NoEventFoundException
from Utils.ApiConfig import ApiConfig

TABLES = {Event.GAME: Table.GAME_ATTENDANCE_TABLE,
          Event.TRAINING: Table.TRAINING_ATTENDANCE_TABLE,
          Event.TIMEKEEPING: Table.TIMEKEEPING_ATTENDANCE_TABLE}


class DataAccess(object):

    def __init__(self, api_config: ApiConfig):
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
        # TODO Add Unsure for each game?
        return user_to_state.add_document_id(doc_id[1].id)

    @dispatch(Game)
    def add(self, game: Game) -> Game:
        doc_ref = self.firebase_repository.add(game, self.tables.get(Table.GAMES_TABLE))
        # TODO add unsure for each player
        return game.add_document_id(doc_ref[1].id)

    @dispatch(Training)
    def add(self, training: Training) -> Training:
        doc_ref = self.firebase_repository.add(training, self.tables.get(Table.TRAININGS_TABLE))
        # TODO add unsure for each player
        return training.add_document_id(doc_ref[1].id)

    @dispatch(TimekeepingEvent)
    def add(self, timekeeping_event: TimekeepingEvent) -> TimekeepingEvent:
        doc_ref = self.firebase_repository.add(timekeeping_event, self.tables.get(Table.TIMEKEEPING_TABLE))
        # TODO add unsure for each player
        return timekeeping_event.add_document_id(doc_ref[1].id)

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

    def update_attendance(self, attendance: Attendance, eventy_type: Event) -> Attendance:
        table = TABLES[eventy_type]
        doc_id = self.firebase_repository.get_event_attendance_doc_id(attendance, table)
        if doc_id is None:
            doc_ref = self.firebase_repository.add(attendance, table)
            doc_id = doc_ref[1].id
            return attendance.add_document_id(doc_id)
        else:
            attendance.add_document_id(doc_id)
            # TODO what if update fails?
            self.firebase_repository.update(attendance, table)
            return attendance

    #######
    # GET #
    #######

    def get_game(self, doc_id: str):
        return self.firebase_repository.get_game(doc_id)

    def get_training(self, doc_id: str):
        return self.firebase_repository.get_training(doc_id)

    def get_timekeeping(self, doc_id: str):
        return self.firebase_repository.get_timekeeping(doc_id)

    def get_attendance(self, telegram_id: str, event_doc_id: str, event_type: Event) -> Attendance:
        user = self.firebase_repository.get_user(telegram_id)
        table = TABLES[event_type]
        try:
            return self.firebase_repository.get_attendance(user, event_doc_id, table)
        except ObjectNotFoundException:
            return Attendance(user.doc_id, event_doc_id, AttendanceState.UNSURE)

    def get_user_state(self, telegram_id: int) -> UsersToState:
        user = self.firebase_repository.get_user(telegram_id)
        return self.firebase_repository.get_user_state(user)

    def get_user(self, telegram_id: int) -> TelegramUser:
        return self.firebase_repository.get_user(telegram_id)

    def get_ordered_games(self) -> [Game]:
        event_list = self.firebase_repository.get_future_events(Table.GAMES_TABLE)
        game_list = []
        for game in event_list:
            new_game = Game.from_dict(game.id, game.to_dict())
            game_list.append(new_game)
        return sorted(game_list, key=lambda g: g.timestamp)

    def get_ordered_trainings(self) -> [Training]:
        event_list = self.firebase_repository.get_future_events(Table.TRAININGS_TABLE)
        training_list = []
        for training in event_list:
            new_training = Training.from_dict(training.id, training.to_dict())
            training_list.append(new_training)
        return sorted(training_list, key=lambda t: t.timestamp)

    def get_ordered_timekeepings(self) -> [TimekeepingEvent]:
        event_list = self.firebase_repository.get_future_events(Table.TIMEKEEPING_TABLE)
        timekeepings_list = []
        for timekeeping in event_list:
            new_timekeeping = TimekeepingEvent.from_dict(timekeeping.id, timekeeping.to_dict())
            timekeepings_list.append(new_timekeeping)
        return sorted(timekeepings_list, key=lambda t: t.timestamp)

    def get_all_players(self) -> [TelegramUser]:
        all_users_to_state = self.firebase_repository.get_all_active_players_to_state()
        all_players = []
        for uts_ref in all_users_to_state:
            uts = UsersToState.from_dict(uts_ref.id, uts_ref.to_dict())
            player = self.firebase_repository.get_user(uts.user_id)
            all_players.append(player)
        return all_players

    def get_stats_event(self, event_id: str, event_type: Event) -> (list, list, list):
        yes = []
        no = []
        unsure = []

        event_attendance_list = self.firebase_repository.get_attendance_list(event_id, table=TABLES[event_type])
        for attendance in event_attendance_list:
            new_attendance = Attendance.from_dict(attendance.id, attendance.to_dict())
            match new_attendance.state:
                case AttendanceState.YES:
                    yes.append(new_attendance.user_id)
                case AttendanceState.NO:
                    no.append(new_attendance.user_id)
                case AttendanceState.UNSURE:
                    unsure.append(new_attendance.user_id)

        all_added_players = set(yes + no + unsure)
        all_users_to_state = self.firebase_repository.get_all_active_players_to_state()
        for element in all_users_to_state:
            user_to_state = UsersToState.from_dict(element.id, element.to_dict())
            user_id = user_to_state.user_id
            if user_id not in all_added_players:
                unsure.append(user_id)

        return yes, no, unsure

    def get_num_of_no_of_event(self, event_id: str, event_type: Event) -> int:
        _, no, unsure = self.get_stats_event(event_id, event_type)
        return len(no)

    def get_names(self, stats: (list, list, list)):
        yes, no, unsure = stats
        yes_with_names = self.add_names(yes)
        no_with_names = self.add_names(no)
        unsure_with_names = self.add_names(unsure)
        return yes_with_names, no_with_names, unsure_with_names

    def add_names(self, doc_id_list: list) -> list[TelegramUser]:
        result = []
        for doc in doc_id_list:
            user_ref = self.firebase_repository.get_document(doc, Table.USERS_TABLE)
            user = TelegramUser.from_dict(user_ref.id, user_ref.to_dict())
            result.append(user)
        return result

    def any_events_in_future(self, event_table: Table, x=42):
        try:
            self.firebase_repository.get_future_events(event_table)
        except NoEventFoundException:
            return False
        return True

    def get_all_event_attendances(self, telegram_user: TelegramUser):
        attendance_dict = {}
        all_events = [Event.GAME, Event.TIMEKEEPING, Event.TRAINING]
        for event in all_events:
            event_attendance_list = self.firebase_repository.get_all_user_event_attendance(telegram_user, event)
            for attendance in event_attendance_list:
                new_attendance = Attendance.from_dict(attendance.id, attendance.to_dict())
                attendance_dict[new_attendance.event_id] = new_attendance
        return attendance_dict

    ##########
    # DELETE #
    ##########
    def delete_event(self, event_type: Event, doc_id: str):
        match event_type:
            case Event.GAME:
                self.firebase_repository.delete_game(doc_id)
            case Event.TRAINING:
                self.firebase_repository.delete_training(doc_id)
            case Event.TIMEKEEPING:
                self.firebase_repository.delete_timekeeping(doc_id)
