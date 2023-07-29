import configparser

from src.Data.FirebaseRepository import FirebaseRepository
from src.States.AttendanceState import AttendanceState
from src.States.PlayerState import PlayerState
from src.Utils.Multidispatch import multidispatch
from src.databaseEntities.Game import Game
from src.databaseEntities.Player import Player
from src.databaseEntities.PlayerToState import PlayerToState
from src.databaseEntities.TimekeepingEvent import TimekeepingEvent
from src.databaseEntities.Training import Training


class FirebaseService(object):
    # TODO Add retry / error handling logic, call via this method all db_access
    def __init__(self, api_config: configparser.RawConfigParser):
        self.firebase_repository = FirebaseRepository(api_config)

    # ADD

    @multidispatch(Player)
    def add(self, player):
        doc_ref = self.firebase_repository.add_player(player)
        player_to_state = PlayerToState(doc_ref[1].id, PlayerState.INIT)
        self.firebase_repository.add_player_to_state(player_to_state)

    @multidispatch(Game)
    def add(self, game):
        self.firebase_repository.add_game(game)

    @multidispatch(Training)
    def add(self, training):
        self.firebase_repository.add_training(training)

    @multidispatch(TimekeepingEvent)
    def add(self, timekeeping_event):
        self.firebase_repository.add_timekeeping_event(timekeeping_event)

    # UPDATE
    @multidispatch(Player)
    def update(self, player):
        pass  # TODO

    @multidispatch(Game)
    def update(self, game):
        pass  # TODO

    @multidispatch(Training)
    def update(self, training):
        pass  # TODO

    @multidispatch(TimekeepingEvent)
    def update(self, timekeeping_event):
        pass  # TODO

    def update_player_to_game_state(self, telegram_id: int, new_state: AttendanceState):
        # get game_id from playerState table
        player_state = self.firebase_repository.get_player_state(telegram_id)
        game_id = player_state.additional_info
        # does it already exist?

        # create new one

    def update_player_state(self, telegram_id: int, new_state: PlayerState):
        player_id = self.firebase_repository.get_player_id_from_telegram_id(telegram_id)
        document_id = self.firebase_repository.get_player_to_state_document(player_id)
        self.firebase_repository.update_player_state(document_id, new_state)
