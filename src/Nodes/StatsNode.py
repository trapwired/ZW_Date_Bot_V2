from functools import partial

from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState

from databaseEntities.UsersToState import UsersToState

from src.Utils import PrintUtils
from src.Utils.CustomExceptions import NoEventFoundException


class StatsNode(Node):
    def add_game_transitions(self):
        # Get all Games
        try:
            games = self.data_access.get_ordered_games()
        except NoEventFoundException as e:
            # TODO send back on click: no games upcoming in future
            return
        # Loop over games, add transition for each
        for game in games:
            # TODO get summary of who is present, pass to prettyPrint
            game_stats = self.data_access.get_stats_game(game.doc_id)
            # TODO remove game_stats, data is old and cant be udpated?
            game_string = PrintUtils.pretty_print_game(game, game_stats)
            game_function = partial(self.handle_doc_id, document_id=game.doc_id)
            self.add_transition(command=game_string, action=game_function, needs_description=False)

    async def handle_doc_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str):
        stats = self.data_access.get_stats_game(document_id)
        stats_with_names = self.data_access.get_names(stats)
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message='Got game with doc id: ' + document_id)

    async def handle_games(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_GAMES)

    async def handle_trainings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_TRAININGS)

    async def handle_timekeepings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_TIMEKEEPINGS)

    async def handle_overview(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # Distinguish UsersToState?
        await self.telegram_service.send_message(
            update=update,
            all_commands=self.get_commands(user_to_state.role, new_state),
            message_type=MessageType.STATS_OVERVIEW)
