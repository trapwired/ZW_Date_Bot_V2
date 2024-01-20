import logging
from functools import partial
from typing import Callable

import telegram
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT

from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from Enums.Table import Table
from Enums.Event import Event
from Enums.MessageType import MessageType
from Enums.CallbackOption import CallbackOption

from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.UserStateService import UserStateService
from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService

from Nodes.Node import Node
from Nodes.DefaultNode import DefaultNode
from Nodes.InitNode import InitNode
from Nodes.RejectedNode import RejectedNode
from Nodes.StatsNode import StatsNode
from Nodes.EditNode import EditNode
from Nodes.AdminNode import AdminNode
from Nodes.UpdateNode import UpdateNode
from Nodes.EditEventTimestampNode import EditEventTimestampNode
from Nodes.EditEventLocationOrOpponentNode import EditEventLocationOrOpponentNode

from Nodes.EditCallbackNode import EditCallbackNode
from Nodes.UpdateEventCallbackNode import UpdateEventCallbackNode

from Data.DataAccess import DataAccess

from Utils.CustomExceptions import NodesMissingException, ObjectNotFoundException, MissingCommandDescriptionException
from Utils.CommandDescriptions import CommandDescriptions
from Utils import NodeUtils
from Utils import CallbackUtils
from Utils.ApiConfig import ApiConfig


def add_nodes_reference_to_all_nodes(nodes: dict):
    for node in nodes.values():
        node.add_nodes(nodes)


def check_all_user_states_have_node(nodes: dict):
    missing_states = []
    for state in UserState:
        if state not in nodes:
            missing_states.append(state)
    if len(missing_states) > 0:
        raise NodesMissingException(missing_states)


def check_all_commands_have_description(nodes: dict):
    missing_commands = []
    command_set = set()
    for node in nodes.values():
        for transition in node.transitions:
            if transition.needs_description:
                command_set.add(transition.command)

    descriptions = CommandDescriptions.descriptions
    for command in command_set:
        if command not in descriptions:
            missing_commands.append(command)

    if len(missing_commands) > 0:
        raise MissingCommandDescriptionException(missing_commands)


class NodeHandler(BaseHandler[Update, CCT]):
    GROUP_TYPES = [ChatType.GROUP, ChatType.SUPERGROUP]

    def __init__(self, bot: telegram.Bot, api_config: ApiConfig, telegram_service: TelegramService,
                 user_state_service: UserStateService, admin_service: AdminService, ics_service: IcsService,
                 data_access: DataAccess, trigger_service: TriggerService):
        super().__init__(self.handle_message)
        self.bot = bot
        self.user_state_service = user_state_service
        self.admin_service = admin_service
        self.data_access = data_access
        self.telegram_service = telegram_service

        self.node_transition_arguments = {}

        self.nodes = self.initialize_nodes(telegram_service, user_state_service, data_access, api_config)
        self.callback_nodes = self.initialize_callback_nodes(telegram_service, data_access, trigger_service,
                                                             ics_service, user_state_service)
        add_nodes_reference_to_all_nodes(self.nodes)

        self.do_checks(api_config)

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logging.info(update)
            chat_type = update.effective_chat.type

            if chat_type in self.GROUP_TYPES:
                # Handle group messages
                return

            if update.callback_query:
                callback_node = self.get_callback_node(update)
                await callback_node.handle(update)
                return

            if not update.message or not update.message.text:
                # Handle pictures and else
                return

            users_to_state, node = self.get_user_state_and_node(update)
            await node.handle(update, users_to_state)
        except Exception as e:
            await self.telegram_service.send_maintainer_message('Exception caught in NodeHandler.handle()', update, e)

    def get_user_state_and_node(self, update):
        telegram_id = update.effective_chat.id
        try:
            users_to_state = self.user_state_service.get_user_state(telegram_id)
            user_state = users_to_state.state
        except ObjectNotFoundException:
            users_to_state = None
            user_state = UserState.INIT

        node = self.nodes[user_state]
        return users_to_state, node

    def initialize_nodes(self, telegram_service: TelegramService, user_state_service: UserStateService,
                         data_access: DataAccess, api_config: ApiConfig):

        init_node = InitNode(UserState.INIT, telegram_service, user_state_service, data_access, api_config, self.bot)
        init_node.add_transition('/start', init_node.handle_start, allowed_roles=RoleSet.REALLY_EVERYONE)

        rejected_node = RejectedNode(UserState.INIT, telegram_service, user_state_service, data_access)
        rejected_node.add_transition(
            api_config.get_key('Chats', 'SPECTATOR_PASSWORD'),
            rejected_node.handle_correct_password,
            new_state=UserState.DEFAULT,
            allowed_roles=RoleSet.REJECTED,
            needs_description=False)

        default_node = DefaultNode(UserState.DEFAULT, telegram_service, user_state_service, data_access)
        default_node.add_transition('/website', default_node.handle_website)
        default_node.add_transition('/stats', new_state=UserState.STATS, message_type=MessageType.STATS_OVERVIEW)
        default_node.add_transition('/edit', new_state=UserState.EDIT, allowed_roles=RoleSet.PLAYERS,
                                    message_type=MessageType.EDIT_OVERVIEW)
        default_node.add_transition('/admin', new_state=UserState.ADMIN, allowed_roles=RoleSet.ADMINS,
                                    message_type=MessageType.ADMIN)

        stats_node = StatsNode(UserState.STATS, telegram_service, user_state_service, data_access)
        stats_node.add_continue_later()
        stats_node.add_transition(
            '/games', message_type=MessageType.STATS_TO_GAMES,
            new_state=UserState.STATS_GAMES,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.GAMES_TABLE))
        stats_node.add_transition(
            '/trainings', message_type=MessageType.STATS_TO_TRAININGS,
            new_state=UserState.STATS_TRAININGS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TRAININGS_TABLE))
        stats_node.add_transition(
            '/timekeepings', message_type=MessageType.STATS_TO_TIMEKEEPINGS,
            new_state=UserState.STATS_TIMEKEEPINGS, allowed_roles=RoleSet.PLAYERS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TIMEKEEPING_TABLE))

        stats_games_node = StatsNode(UserState.STATS_GAMES, telegram_service, user_state_service, data_access)
        stats_games_node.add_continue_later()
        stats_games_node.add_transition('Overview', message_type=MessageType.STATS_OVERVIEW, new_state=UserState.STATS)
        self.add_event_transitions_to_node(Event.GAME, stats_games_node, stats_games_node.handle_event_id)

        stats_trainings_node = StatsNode(UserState.STATS_TRAININGS, telegram_service, user_state_service, data_access)
        stats_trainings_node.add_continue_later()
        stats_trainings_node.add_transition('Overview', message_type=MessageType.STATS_OVERVIEW,
                                            new_state=UserState.STATS)
        self.add_event_transitions_to_node(Event.TRAINING, stats_trainings_node,
                                           stats_trainings_node.handle_event_id)

        stats_timekeepings_node = StatsNode(UserState.STATS_TIMEKEEPINGS, telegram_service, user_state_service,
                                            data_access)
        stats_timekeepings_node.add_continue_later()
        stats_timekeepings_node.add_transition('Overview', message_type=MessageType.STATS_OVERVIEW,
                                               new_state=UserState.STATS)
        self.add_event_transitions_to_node(Event.TIMEKEEPING, stats_timekeepings_node,
                                           stats_timekeepings_node.handle_event_id)

        edit_node = EditNode(UserState.EDIT, telegram_service, user_state_service, data_access)
        edit_node.add_continue_later()
        edit_node.add_transition(
            '/games', message_type=MessageType.EDIT_TO_GAMES,
            new_state=UserState.EDIT_GAMES,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.GAMES_TABLE))
        edit_node.add_transition(
            '/trainings', message_type=MessageType.EDIT_TO_TRAININGS,
            new_state=UserState.EDIT_TRAININGS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TRAININGS_TABLE))
        edit_node.add_transition(
            '/timekeepings', message_type=MessageType.EDIT_TO_TIMEKEEPINGS,
            new_state=UserState.EDIT_TIMEKEEPINGS, allowed_roles=RoleSet.PLAYERS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TIMEKEEPING_TABLE))

        edit_games_node = EditNode(UserState.EDIT_GAMES, telegram_service, user_state_service, data_access)
        edit_games_node.add_continue_later()
        edit_games_node.add_transition('Overview', message_type=MessageType.EDIT_OVERVIEW, new_state=UserState.EDIT)
        self.add_event_transitions_to_node(Event.GAME, edit_games_node, edit_games_node.handle_event_id)

        edit_trainings_node = EditNode(UserState.EDIT_TRAININGS, telegram_service, user_state_service, data_access)
        edit_trainings_node.add_continue_later()
        edit_trainings_node.add_transition('Overview', message_type=MessageType.EDIT_OVERVIEW, new_state=UserState.EDIT)
        self.add_event_transitions_to_node(Event.TRAINING, edit_trainings_node,
                                           edit_trainings_node.handle_event_id)

        edit_timekeepings_node = EditNode(UserState.EDIT_TIMEKEEPINGS, telegram_service, user_state_service,
                                          data_access)
        edit_timekeepings_node.add_continue_later()
        edit_timekeepings_node.add_transition('Overview', message_type=MessageType.EDIT_OVERVIEW,
                                              new_state=UserState.EDIT)
        self.add_event_transitions_to_node(Event.TIMEKEEPING, edit_timekeepings_node,
                                           edit_timekeepings_node.handle_event_id)

        admin_node = AdminNode(UserState.ADMIN, telegram_service, user_state_service, data_access)
        admin_node.add_continue_later()
        admin_node.add_transition('/add', message_type=MessageType.ADMIN_ADD, new_state=UserState.ADMIN_ADD)
        admin_node.add_transition('/update', message_type=MessageType.ADMIN_UPDATE, new_state=UserState.ADMIN_UPDATE)
        admin_node.add_transition('/statistics', admin_node.handle_statistics)

        admin_add_node = AdminNode(UserState.ADMIN_ADD, telegram_service, user_state_service, data_access)
        admin_add_node.add_continue_later()
        admin_add_node.add_transition('Overview', message_type=MessageType.ADMIN, new_state=UserState.ADMIN)

        admin_update_node = AdminNode(UserState.ADMIN_UPDATE, telegram_service, user_state_service, data_access)
        admin_update_node.add_continue_later()
        admin_update_node.add_transition('Overview', message_type=MessageType.ADMIN, new_state=UserState.ADMIN)
        admin_update_node.add_transition(
            '/games', message_type=MessageType.ADMIN_UPDATE_TO_GAME,
            new_state=UserState.ADMIN_UPDATE_GAME,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.GAMES_TABLE))
        admin_update_node.add_transition(
            '/trainings', message_type=MessageType.ADMIN_UPDATE_TO_TRAINING,
            new_state=UserState.ADMIN_UPDATE_TRAINING,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TRAININGS_TABLE))
        admin_update_node.add_transition(
            '/timekeepings', message_type=MessageType.ADMIN_UPDATE_TO_TIMEKEEPING,
            new_state=UserState.ADMIN_UPDATE_TIMEKEEPING, allowed_roles=RoleSet.PLAYERS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TIMEKEEPING_TABLE))

        update_games_node = UpdateNode(UserState.ADMIN_UPDATE_GAME, telegram_service, user_state_service, data_access)
        update_games_node.add_continue_later()
        update_games_node.add_transition('Overview', message_type=MessageType.ADMIN_UPDATE,
                                         new_state=UserState.ADMIN_UPDATE)
        self.add_event_transitions_to_node(Event.GAME, update_games_node, update_games_node.handle_event_id)

        update_trainings_node = UpdateNode(UserState.ADMIN_UPDATE_TRAINING, telegram_service, user_state_service,
                                           data_access)
        update_trainings_node.add_continue_later()
        update_trainings_node.add_transition('Overview', message_type=MessageType.ADMIN_UPDATE,
                                             new_state=UserState.ADMIN_UPDATE)
        self.add_event_transitions_to_node(Event.TRAINING, update_trainings_node,
                                           update_trainings_node.handle_event_id)

        update_timekeepings_node = UpdateNode(UserState.ADMIN_UPDATE_TIMEKEEPING, telegram_service, user_state_service,
                                              data_access)
        update_timekeepings_node.add_continue_later()
        update_timekeepings_node.add_transition('Overview', message_type=MessageType.ADMIN_UPDATE,
                                                new_state=UserState.ADMIN_UPDATE)
        self.add_event_transitions_to_node(Event.TIMEKEEPING, update_timekeepings_node,
                                           update_timekeepings_node.handle_event_id)

        admin_update_game_timestamp_node = EditEventTimestampNode(
            UserState.ADMIN_UPDATE_GAME_TIMESTAMP, telegram_service, user_state_service, data_access, Event.GAME, self)

        admin_update_training_timestamp_node = EditEventTimestampNode(
            UserState.ADMIN_UPDATE_TRAINING_TIMESTAMP, telegram_service, user_state_service, data_access,
            Event.TRAINING, self)

        admin_update_timekeeping_timestamp_node = EditEventTimestampNode(
            UserState.ADMIN_UPDATE_TIMEKEEPING_TIMESTAMP, telegram_service, user_state_service, data_access,
            Event.TIMEKEEPING, self)

        admin_update_game_opponent_node = EditEventLocationOrOpponentNode(
            UserState.ADMIN_UPDATE_GAME_OPPONENT, telegram_service, user_state_service, data_access, Event.GAME,
            CallbackOption.OPPONENT, self)

        admin_update_game_location_node = EditEventLocationOrOpponentNode(
            UserState.ADMIN_UPDATE_GAME_LOCATION, telegram_service, user_state_service, data_access, Event.GAME,
            CallbackOption.LOCATION, self)

        admin_update_training_location_node = EditEventLocationOrOpponentNode(
            UserState.ADMIN_UPDATE_TRAINING_LOCATION, telegram_service, user_state_service, data_access, Event.TRAINING,
            CallbackOption.LOCATION, self)

        admin_update_timekeeping_location_node = EditEventLocationOrOpponentNode(
            UserState.ADMIN_UPDATE_TIMEKEEPING_LOCATION, telegram_service, user_state_service, data_access,
            Event.TIMEKEEPING, CallbackOption.LOCATION, self)

        all_nodes_dict = {
            UserState.INIT: init_node,
            UserState.REJECTED: rejected_node,
            UserState.DEFAULT: default_node,
            UserState.STATS: stats_node,
            UserState.STATS_GAMES: stats_games_node,
            UserState.STATS_TRAININGS: stats_trainings_node,
            UserState.STATS_TIMEKEEPINGS: stats_timekeepings_node,
            UserState.EDIT: edit_node,
            UserState.EDIT_GAMES: edit_games_node,
            UserState.EDIT_TRAININGS: edit_trainings_node,
            UserState.EDIT_TIMEKEEPINGS: edit_timekeepings_node,
            UserState.ADMIN: admin_node,
            UserState.ADMIN_ADD: admin_add_node,
            UserState.ADMIN_UPDATE: admin_update_node,
            UserState.ADMIN_UPDATE_GAME: update_games_node,
            UserState.ADMIN_UPDATE_TRAINING: update_trainings_node,
            UserState.ADMIN_UPDATE_TIMEKEEPING: update_timekeepings_node,
            UserState.ADMIN_UPDATE_GAME_OPPONENT: admin_update_game_opponent_node,
            UserState.ADMIN_UPDATE_GAME_LOCATION: admin_update_game_location_node,
            UserState.ADMIN_UPDATE_GAME_TIMESTAMP: admin_update_game_timestamp_node,
            UserState.ADMIN_UPDATE_TRAINING_LOCATION: admin_update_training_location_node,
            UserState.ADMIN_UPDATE_TRAINING_TIMESTAMP: admin_update_training_timestamp_node,
            UserState.ADMIN_UPDATE_TIMEKEEPING_LOCATION: admin_update_timekeeping_location_node,
            UserState.ADMIN_UPDATE_TIMEKEEPING_TIMESTAMP: admin_update_timekeeping_timestamp_node
        }

        return all_nodes_dict

    def initialize_callback_nodes(self, telegram_service: TelegramService, data_access: DataAccess,
                                  trigger_service: TriggerService, ics_service: IcsService, user_state_service: UserStateService):
        edit_callback_node = EditCallbackNode(telegram_service, data_access, trigger_service, ics_service)
        update_callback_node = UpdateEventCallbackNode(telegram_service, data_access, trigger_service, self,
                                                       user_state_service)

        callback_nodes_dict = {
            UserState.EDIT: edit_callback_node,
            UserState.ADMIN_UPDATE: update_callback_node
        }
        return callback_nodes_dict

    def add_event_transitions_to_node(self, event_type: Event, node: Node, event_function: Callable):
        if node not in self.node_transition_arguments.keys():
            self.node_transition_arguments[node] = []
        self.node_transition_arguments[node].append((event_type, event_function))

        NodeUtils.add_event_transitions_to_node(event_type, node, event_function)

    def recalculate_node_transitions(self):
        for node, argument_list in self.node_transition_arguments.items():
            node.clear_event_transitions()
            for event_type, event_function in argument_list:
                NodeUtils.add_event_transitions_to_node(event_type, node, event_function)

    def do_checks(self, api_config: ApiConfig):
        check_all_user_states_have_node(self.nodes)
        check_all_commands_have_description(self.nodes)

    def get_callback_node(self, update):
        query = update.callback_query
        callback_message = CallbackUtils.try_parse_callback_message(query.data)
        if callback_message is None:
            raise Exception('Parsing of Callback message failed: ', query.data)

        user_state, _, _, _ = callback_message

        if not self.callback_nodes[user_state]:
            raise Exception('No callback-node found for user_state: ', user_state)
        return self.callback_nodes[user_state]
