import configparser

from Data.FirebaseRepository import FirebaseRepository
from Enums.AttendanceState import AttendanceState
from Enums.PlayerState import PlayerState
from Exceptions.ObjectNotFoundException import ObjectNotFoundException
from Utils.Multidispatch import multidispatch
from databaseEntities.Game import Game
from databaseEntities.Player import Player
from databaseEntities.PlayerToState import PlayerToState
from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training


class DataAccess(object):

    def __init__(self, api_config: configparser.RawConfigParser):
        self.firebase_repository = FirebaseRepository(api_config)

    @multidispatch(Player)
    def add(self, player) -> Player:
        doc_ref = self.firebase_repository.add_player(player)
        doc_id = doc_ref[1].id
        player_to_state = PlayerToState(doc_id, PlayerState.INIT)
        self.firebase_repository.add_player_to_state(player_to_state)
        return player.add_document_id(doc_id)

    @multidispatch(Game)
    def add(self, game: Game) -> Game:
        doc_ref = self.firebase_repository.add_game(game)
        doc_id = doc_ref[1].id
        return game.add_document_id(doc_id)

    @multidispatch(Training)
    def add(self, training: Training) -> Training:
        doc_ref = self.firebase_repository.add_training(training)
        doc_id = doc_ref[1].id
        return training.add_document_id(doc_id)

    @multidispatch(TimekeepingEvent)
    def add(self, timekeeping_event: TimekeepingEvent) -> TimekeepingEvent:
        doc_ref = self.firebase_repository.add_timekeeping_event(timekeeping_event)
        doc_id = doc_ref[1].id
        return timekeeping_event.add_document_id(doc_id)

    # UPDATE

    @multidispatch(PlayerToState)
    def update(self, player_to_state: PlayerToState):
        if player_to_state.doc_id is None:
            self.firebase_repository.update_player_state_via_player_id(player_to_state)
        else:
            self.firebase_repository.update_player_state(player_to_state)

    def get_player_state(self, telegram_id: int) -> PlayerToState:
        player = self.firebase_repository.get_player(telegram_id)
        return self.firebase_repository.get_player_state(player)

    ################################
    # CURSOR - ONLY FINISHED ABOVE #
    ################################

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

    def update_player_to_game_state(self, telegram_id: int, new_state: AttendanceState):  # TODO WIP
        # get game_id from playerState table
        player_state = self.firebase_repository.get_player_state(telegram_id)
        game_id = player_state.additional_info
        # does it already exist?

        # create new one
