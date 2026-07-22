import pandas as pd
from multipledispatch import dispatch

from data.RepositoryFactory import create_repository
from data.Tables import EVENT_ATTENDANCE_TABLES

from Enums.UserState import UserState
from Enums.Table import Table
from Enums.Role import Role
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.EventField import EventField

from domain.entities.Game import Game
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.UsersToState import UsersToState
from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training
from domain.entities.Attendance import Attendance
from domain.entities.PlayerMetric import PlayerMetric
from domain.entities.TempData import TempData
from domain.entities.Settings import Settings

from Utils import PrintUtils
from Utils.CustomExceptions import ObjectNotFoundException, DocumentIdNotPresentException
from Utils.ApiConfig import ApiConfig

class DataAccess(object):

    def __init__(self, api_config: ApiConfig, repository=None):
        # Injection seam for tests (in-memory backend); production resolves via config.
        self.repository = repository or create_repository(api_config)

    #######
    # ADD #
    #######

    @dispatch(TelegramUser)
    def add(self, user: TelegramUser) -> UsersToState:
        user_doc_id = self.repository.add(user, Table.USERS_TABLE)
        user_to_state = UsersToState(user_doc_id, UserState.INIT)
        doc_id = self.repository.add(user_to_state, Table.USERS_TO_STATE_TABLE)
        return user_to_state.add_document_id(doc_id)

    @dispatch(Game)
    def add(self, game: Game) -> Game:
        doc_id = self.repository.add(game, Table.GAMES_TABLE)
        return game.add_document_id(doc_id)

    @dispatch(Training)
    def add(self, training: Training) -> Training:
        doc_id = self.repository.add(training, Table.TRAININGS_TABLE)
        return training.add_document_id(doc_id)

    @dispatch(TimekeepingEvent)
    def add(self, timekeeping_event: TimekeepingEvent) -> TimekeepingEvent:
        doc_id = self.repository.add(timekeeping_event, Table.TIMEKEEPING_TABLE)
        return timekeeping_event.add_document_id(doc_id)

    @dispatch(TempData)
    def add(self, temp_data: TempData) -> TempData:
        doc_id = self.repository.add(temp_data, Table.TEMP_DATA_TABLE)
        return temp_data.add_document_id(doc_id)

    @dispatch(Team)
    def add(self, team: Team) -> Team:
        doc_id = self.repository.add(team, Table.TEAMS_TABLE)
        return team.add_document_id(doc_id)

    ##########
    # UPDATE #
    ##########

    def update_event_field(self, event_type: Event, event_id: str, new_value: str | pd.Timestamp,
                           field_type: EventField):
        match event_type:
            case Event.GAME:
                event = self.repository.get_game(event_id)
            case Event.TRAINING:
                event = self.repository.get_training(event_id)
            case Event.TIMEKEEPING:
                event = self.repository.get_timekeeping(event_id)
            case _:
                raise ValueError(f'Unhandled event type: {event_type}')

        match field_type:
            case EventField.LOCATION:
                event.location = new_value
            case EventField.DATETIME:
                event.timestamp = new_value
            case EventField.OPPONENT:
                event.opponent = new_value

        return self.update(event)

    @dispatch(UsersToState)
    def update(self, users_to_state: UsersToState):
        if users_to_state.doc_id is None:
            return self.repository.update_user_state_via_user_id(users_to_state)
        else:
            return self.repository.update(users_to_state, Table.USERS_TO_STATE_TABLE)

    @dispatch(TelegramUser)
    def update(self, user: TelegramUser):
        if user.doc_id is None:
            return self.repository.update_user_via_telegram_id(user)
        else:
            return self.repository.update(user, Table.USERS_TABLE)

    @dispatch(Game)
    def update(self, game: Game):
        if game.doc_id is None:
            raise DocumentIdNotPresentException()
        return self.repository.update(game, Table.GAMES_TABLE)

    @dispatch(Training)
    def update(self, training: Training):
        if training.doc_id is None:
            raise DocumentIdNotPresentException()
        return self.repository.update(training, Table.TRAININGS_TABLE)

    @dispatch(PlayerMetric)
    def update(self, player_metric: PlayerMetric):
        if player_metric.doc_id is None:
            raise DocumentIdNotPresentException()
        return self.repository.update(player_metric, Table.PLAYER_METRIC)

    @dispatch(TimekeepingEvent)
    def update(self, timekeeping_event: TimekeepingEvent):
        if timekeeping_event.doc_id is None:
            raise DocumentIdNotPresentException()
        return self.repository.update(timekeeping_event, Table.TIMEKEEPING_TABLE)

    def update_attendance(self, attendance: Attendance, event_type: Event) -> Attendance:
        table = EVENT_ATTENDANCE_TABLES[event_type]
        doc_id = self.repository.get_event_attendance_doc_id(attendance, table)
        if doc_id is None:
            return self._add_attendance(attendance, table)
        attendance.add_document_id(doc_id)
        try:
            self.repository.update(attendance, table)
        except ObjectNotFoundException:
            # The record was deleted between the lookup and the write (a race); recreate it
            # so the player's attendance vote isn't silently lost.
            return self._add_attendance(attendance, table)
        return attendance

    def _add_attendance(self, attendance: Attendance, table: Table) -> Attendance:
        doc_id = self.repository.add(attendance, table)
        return attendance.add_document_id(doc_id)

    @dispatch(TempData)
    def update(self, temp_data: TempData):
        if temp_data.doc_id is None:
            raise DocumentIdNotPresentException()
        return self.repository.update(temp_data, Table.TEMP_DATA_TABLE)

    @dispatch(Team)
    def update(self, team: Team):
        if team.doc_id is None:
            raise DocumentIdNotPresentException()
        return self.repository.update(team, Table.TEAMS_TABLE)

    #######
    # GET #
    #######

    def get_event(self, event_type: Event, doc_id: str):
        match event_type:
            case Event.GAME:
                return self.get_game(doc_id)
            case Event.TRAINING:
                return self.get_training(doc_id)
            case Event.TIMEKEEPING:
                return self.get_timekeeping(doc_id)
            case _:
                raise ValueError(f'Unhandled event type: {event_type}')

    def get_game(self, doc_id: str):
        return self.repository.get_game(doc_id)

    def get_training(self, doc_id: str):
        return self.repository.get_training(doc_id)

    def get_timekeeping(self, doc_id: str):
        return self.repository.get_timekeeping(doc_id)

    def get_attendance(self, telegram_id: str, event_doc_id: str, event_type: Event) -> Attendance:
        user = self.repository.get_user(telegram_id)
        table = EVENT_ATTENDANCE_TABLES[event_type]
        try:
            return self.repository.get_attendance(user, event_doc_id, table)
        except ObjectNotFoundException:
            return Attendance(user.doc_id, event_doc_id, AttendanceState.UNSURE)

    def get_user_state(self, telegram_id: int) -> UsersToState:
        user = self.repository.get_user(telegram_id)
        return self.repository.get_user_state(user)

    def get_user(self, telegram_id: int) -> TelegramUser:
        return self.repository.get_user(telegram_id)

    def get_player_metric(self, telegram_id: int):
        user = self.repository.get_user(telegram_id)
        return self.repository.get_player_metric(user)

    def get_ordered_games(self) -> [Game]:
        event_list = self.repository.get_future_events(Table.GAMES_TABLE)
        game_list = []
        for game in event_list:
            new_game = Game.from_dict(game.id, game.to_dict())
            game_list.append(new_game)
        return sorted(game_list, key=lambda g: g.timestamp)

    def get_ordered_trainings(self) -> [Training]:
        event_list = self.repository.get_future_events(Table.TRAININGS_TABLE)
        training_list = []
        for training in event_list:
            new_training = Training.from_dict(training.id, training.to_dict())
            training_list.append(new_training)
        return sorted(training_list, key=lambda t: t.timestamp)

    def get_ordered_timekeepings(self) -> [TimekeepingEvent]:
        event_list = self.repository.get_future_events(Table.TIMEKEEPING_TABLE)
        timekeepings_list = []
        for timekeeping in event_list:
            new_timekeeping = TimekeepingEvent.from_dict(timekeeping.id, timekeeping.to_dict())
            timekeepings_list.append(new_timekeeping)
        return sorted(timekeepings_list, key=lambda t: t.timestamp)

    def get_all_players(self) -> [TelegramUser]:
        all_users_to_state = self.repository.get_all_active_players_to_state()
        all_players = []
        for uts_ref in all_users_to_state:
            uts = UsersToState.from_dict(uts_ref.id, uts_ref.to_dict())
            player = self.repository.get_user(uts.user_id)
            all_players.append(player)
        return all_players

    def get_users_to_state_by_role(self, role: Role) -> [UsersToState]:
        rows = self.repository.get_users_to_state_by_role(role)
        return [UsersToState.from_dict(row.id, row.to_dict()) for row in rows]

    def get_admins_to_state(self) -> [UsersToState]:
        rows = self.repository.get_admins_to_state()
        return [UsersToState.from_dict(row.id, row.to_dict()) for row in rows]

    def delete_team(self, team: Team) -> None:
        self.repository.delete_team(team.doc_id)

    def get_users_to_state_by_team(self, team_id: str) -> [UsersToState]:
        rows = self.repository.get_users_to_state_by_team(team_id)
        return [UsersToState.from_dict(row.id, row.to_dict()) for row in rows]

    def get_user_by_doc_id(self, user_doc_id: str) -> TelegramUser:
        return self.repository.get_user(user_doc_id)

    def get_user_state_for_user(self, user: TelegramUser) -> UsersToState:
        return self.repository.get_user_state(user)

    def get_team(self, doc_id: str) -> Team:
        return self.repository.get_team(doc_id)

    def get_all_teams(self) -> list[Team]:
        return self.repository.get_all_teams()


    def get_stats_event(self, event_id: str, event_type: Event) -> (list, list, list):
        # Summary rules:
        # - YES lists everyone who said yes, including retired/inactive players.
        # - NO and UNSURE list only active players (ADMIN/PLAYER); a retired/inactive
        #   player surfaces in a summary only by explicitly saying yes.
        # - Active players with no attendance record default to UNSURE.
        yes = []
        no = []
        unsure = []

        active_player_ids = [
            UsersToState.from_dict(element.id, element.to_dict()).user_id
            for element in self.repository.get_all_active_players_to_state()
        ]
        active_player_id_set = set(active_player_ids)

        event_attendance_list = self.repository.get_attendance_list(event_id, table=EVENT_ATTENDANCE_TABLES[event_type])
        for attendance in event_attendance_list:
            new_attendance = Attendance.from_dict(attendance.id, attendance.to_dict())
            user_id = new_attendance.user_id
            is_active = user_id in active_player_id_set
            match new_attendance.state:
                case AttendanceState.YES:
                    yes.append(user_id)
                case AttendanceState.NO:
                    if is_active:
                        no.append(user_id)
                case AttendanceState.UNSURE:
                    if is_active:
                        unsure.append(user_id)

        placed_players = set(yes + no + unsure)
        for user_id in active_player_ids:  # ordered list — keeps summary output stable across runs
            if user_id not in placed_players:
                unsure.append(user_id)

        return yes, no, unsure

    def get_num_of_available_players(self, event_id: str, event_type: Event) -> int:
        yes, _, unsure = self.get_stats_event(event_id, event_type)
        return len(yes) + len(unsure)

    def get_names(self, stats: (list, list, list)):
        yes, no, unsure = stats
        yes_with_names = PrintUtils.sorted_by_display_name(self.add_names(yes))
        no_with_names = PrintUtils.sorted_by_display_name(self.add_names(no))
        unsure_with_names = PrintUtils.sorted_by_display_name(self.add_names(unsure))
        return yes_with_names, no_with_names, unsure_with_names

    def get_temp_data(self, user_id: str) -> TempData:
        return self.repository.get_temp_data(user_id)

    def get_website(self) -> str | None:
        settings = self.repository.get_settings()
        return settings.website if settings else None

    def set_website(self, website: str):
        self.repository.set_settings(Settings(website))

    def add_names(self, doc_id_list: list) -> list[TelegramUser]:
        result = []
        for doc in doc_id_list:
            user_ref = self.repository.get_document(doc, Table.USERS_TABLE)
            user = TelegramUser.from_dict(user_ref.id, user_ref.to_dict())
            result.append(user)
        return result

    def has_any_docs(self, table: Table) -> bool:
        return self.repository.has_any_docs(table)

    def any_events_in_future(self, event_table: Table):
        events = self.repository.get_future_events(event_table)
        return len(events) > 0

    def get_all_event_attendances(self, telegram_user: TelegramUser):
        attendance_dict = {}
        all_events = [Event.GAME, Event.TIMEKEEPING, Event.TRAINING]
        for event in all_events:
            event_attendance_list = self.repository.get_all_user_event_attendance(telegram_user, event)
            for attendance in event_attendance_list:
                new_attendance = Attendance.from_dict(attendance.id, attendance.to_dict())
                attendance_dict[new_attendance.event_id] = new_attendance
        return attendance_dict

    def get_user_to_player_metric(self) -> dict:
        all_player_metrics = self.repository.get_all_player_metrics()
        users_to_player_metric_dict = dict()

        for row in all_player_metrics:
            player_metric = PlayerMetric.from_dict(row.id, row.to_dict())
            user = self.repository.get_user(player_metric.user_id)
            users_to_player_metric_dict[user] = player_metric

        return users_to_player_metric_dict

    def get_attendance_statistics(self, event_type: Event):
        relevant_event_ids = self.repository.get_all_relevant_event_ids(event_type)
        all_attendances = self.repository.get_all_event_attendances(event_type, relevant_event_ids)
        all_active_players = self.repository.get_all_active_players_to_state()
        user_id_to_attendance_dict = dict()

        for active_player in all_active_players:
            user_to_state = UsersToState.from_dict(active_player.id, active_player.to_dict())
            user_id = user_to_state.user_id
            user_id_to_attendance_dict[user_id] = []

        for row in all_attendances:
            attendance = Attendance.from_dict(row.id, row.to_dict())
            if attendance.user_id in user_id_to_attendance_dict.keys():
                user_id_to_attendance_dict[attendance.user_id].append(attendance)

        user_to_attendance_dict = dict()
        for user_id, attendance_list in user_id_to_attendance_dict.items():
            user = self.repository.get_user(user_id)
            user_to_attendance_dict[user] = attendance_list

        return user_to_attendance_dict

    ##########
    # DELETE #
    ##########

    def delete_event(self, event_type: Event, doc_id: str):
        match event_type:
            case Event.GAME:
                self.repository.delete_game(doc_id)
            case Event.TRAINING:
                self.repository.delete_training(doc_id)
            case Event.TIMEKEEPING:
                self.repository.delete_timekeeping(doc_id)
            case _:
                raise ValueError(f'Unhandled event type: {event_type}')
        self.repository.delete_event_attendances(event_type, doc_id)

    @dispatch(TempData)
    def delete(self, temp_data: TempData):
        self.repository.delete_temp_data(temp_data)

    def reset_statistics(self) -> int:
        # Ends the current season: hard-deletes every player's reminder statistics.
        return self.repository.delete_all_player_metrics()

    ########
    # ELSE #
    ########

    def reset_all_player_event_attendance(self, event_type: Event, doc_id: str):
        self.repository.reset_all_player_event_attendance(doc_id, EVENT_ATTENDANCE_TABLES[event_type])
