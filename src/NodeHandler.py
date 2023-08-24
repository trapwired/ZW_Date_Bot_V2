import configparser
import logging
from functools import partial

import telegram
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT

from Enums.UserState import UserState
from Enums.RoleSet import RoleSet
from Enums.Table import Table
from Enums.Event import Event

from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.UserStateService import UserStateService
from Services.TelegramService import TelegramService

from Nodes.DefaultNode import DefaultNode
from Nodes.InitNode import InitNode
from Nodes.RejectedNode import RejectedNode
from Nodes.StatsNode import StatsNode
from Nodes.EditNode import EditNode

from Data.DataAccess import DataAccess

from Utils.CustomExceptions import NodesMissingException, ObjectNotFoundException, MissingCommandDescriptionException
from Utils.CommandDescriptions import CommandDescriptions


def initialize_services(bot: telegram.Bot, api_config: configparser.RawConfigParser):
    data_access = DataAccess(api_config)
    telegram_service = TelegramService(bot)
    user_state_service = UserStateService(data_access)
    admin_service = AdminService(data_access)
    ics_service = IcsService(data_access)
    return telegram_service, user_state_service, admin_service, ics_service, data_access


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


def check_all_commands_have_description(nodes: dict, api_config: configparser.RawConfigParser):
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

    def __init__(self, bot: telegram.Bot, api_config: configparser.RawConfigParser):
        super().__init__(self.handle_message)
        self.bot = bot
        telegram_service, user_state_service, admin_service, ics_service, data_access = \
            initialize_services(bot, api_config)
        self.user_state_service = user_state_service
        self.admin_service = admin_service
        self.data_access = data_access

        self.nodes = self.initialize_nodes(telegram_service, user_state_service, data_access, api_config)
        add_nodes_reference_to_all_nodes(self.nodes)

        self.do_checks(api_config)

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.info(update)
        chat_type = update.effective_chat.type
        if chat_type in self.GROUP_TYPES:
            return
        if not update.message.text:
            return

        users_to_state, node = self.get_user_state_and_workflow(update)
        await node.handle(update, users_to_state)

    def get_user_state_and_workflow(self, update):
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
                         data_access: DataAccess, api_config: configparser.RawConfigParser):

        init_node = InitNode(UserState.INIT, telegram_service, user_state_service, data_access, api_config, self.bot)
        init_node.add_transition('/start', init_node.handle_start, allowed_roles=RoleSet.REALLY_EVERYONE)

        rejected_node = RejectedNode(UserState.INIT, telegram_service, user_state_service, data_access)
        rejected_node.add_transition(
            api_config['Chats']['SPECTATOR_PASSWORD'],
            rejected_node.handle_correct_password,
            new_state=UserState.DEFAULT,
            allowed_roles=RoleSet.REJECTED,
            needs_description=False)

        default_node = DefaultNode(UserState.DEFAULT, telegram_service, user_state_service, data_access)
        default_node.add_transition('/website', default_node.handle_website)
        default_node.add_transition('/stats', default_node.handle_stats, new_state=UserState.STATS)
        default_node.add_transition('/edit', default_node.handle_edit, new_state=UserState.EDIT,
                                    allowed_roles=RoleSet.PLAYERS)

        stats_node = StatsNode(UserState.STATS, telegram_service, user_state_service, data_access)
        stats_node.add_continue_later()
        stats_node.add_transition(
            '/games', stats_node.handle_games,
            new_state=UserState.STATS_GAMES,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.GAMES_TABLE))
        stats_node.add_transition(
            '/trainings', stats_node.handle_trainings,
            new_state=UserState.STATS_TRAININGS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TRAININGS_TABLE))
        stats_node.add_transition(
            '/timekeepings', stats_node.handle_timekeepings,
            new_state=UserState.STATS_TIMEKEEPINGS,
            is_active_function=partial(self.data_access.any_events_in_future, event_table=Table.TIMEKEEPING_TABLE))

        stats_games_node = StatsNode(UserState.STATS_GAMES, telegram_service, user_state_service, data_access)
        stats_games_node.add_continue_later()
        stats_games_node.add_transition('Overview', stats_node.handle_overview, new_state=UserState.STATS)
        stats_games_node.add_event_transitions(Event.GAME)

        stats_trainings_node = StatsNode(UserState.STATS_TRAININGS, telegram_service, user_state_service, data_access)
        stats_trainings_node.add_continue_later()
        stats_trainings_node.add_transition('Overview', stats_node.handle_overview, new_state=UserState.STATS)
        stats_trainings_node.add_event_transitions(Event.TRAINING)

        stats_timekeepings_node = StatsNode(UserState.STATS_TIMEKEEPINGS, telegram_service, user_state_service,
                                            data_access)
        stats_timekeepings_node.add_continue_later()
        stats_timekeepings_node.add_transition('Overview', stats_node.handle_overview, new_state=UserState.STATS)
        stats_timekeepings_node.add_event_transitions(Event.TIMEKEEPING)

        edit_node = EditNode(UserState.EDIT, telegram_service, user_state_service, data_access)
        edit_node.add_continue_later()

        all_nodes_dict = {
            UserState.INIT: init_node,
            UserState.REJECTED: rejected_node,
            UserState.DEFAULT: default_node,
            UserState.STATS: stats_node,
            UserState.STATS_GAMES: stats_games_node,
            UserState.STATS_TRAININGS: stats_trainings_node,
            UserState.STATS_TIMEKEEPINGS: stats_timekeepings_node,
            UserState.EDIT: edit_node
        }

        return all_nodes_dict

    def do_checks(self, api_config: configparser.RawConfigParser):
        check_all_user_states_have_node(self.nodes)
        check_all_commands_have_description(self.nodes, api_config)
