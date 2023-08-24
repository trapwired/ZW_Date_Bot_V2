from functools import partial

from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils
from Utils.CustomExceptions import NoEventFoundException


class StatsNode(Node):
    def add_event_transitions(self, event_type: Event):
        try:
            events = []
            match event_type:
                case Event.GAME:
                    events = self.data_access.get_ordered_games()
                case Event.TRAINING:
                    events = self.data_access.get_ordered_trainings()
                case Event.TIMEKEEPING:
                    events = self.data_access.get_ordered_timekeepings()
        except NoEventFoundException as e:
            return

        for event in events:
            event_string = PrintUtils.pretty_print(event)
            event_function = self.handle_doc_id
            self.add_transition(command=event_string, action=event_function, needs_description=False,
                                document_id=event.doc_id)

    async def handle_doc_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str):
        stats = self.data_access.get_stats_game(document_id)
        stats_with_names = self.data_access.get_names(stats)
        message = PrintUtils.pretty_print_game_summary(stats_with_names, update.message.text)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message)

    async def handle_games(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_GAMES)

    async def handle_trainings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_TRAININGS)

    async def handle_timekeepings(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.STATS_TO_TIMEKEEPINGS)

    async def handle_overview(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # Distinguish UsersToState?
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.STATS_OVERVIEW)
