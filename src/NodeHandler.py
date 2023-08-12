import configparser
import logging

import telegram
from telegram import Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT

from Enums.UserState import UserState
from Exceptions.ObjectNotFoundException import ObjectNotFoundException
from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.UserStateService import UserStateService
from Services.TelegramService import TelegramService
from Nodes.DefaultNode import DefaultNode
from Nodes.InitNode import InitNode
from Nodes.RejectedNode import RejectedNode
from Nodes.StatsNode import StatsNode
from Data.DataAccess import DataAccess
from src.Enums.RoleSet import RoleSet


def initialize_services(bot: telegram.Bot, api_config: configparser.RawConfigParser):
    data_access = DataAccess(api_config)
    telegram_service = TelegramService(bot)
    user_state_service = UserStateService(data_access)
    admin_service = AdminService(data_access)
    ics_service = IcsService(data_access)
    return telegram_service, user_state_service, admin_service, ics_service, data_access


class NodeHandler(BaseHandler[Update, CCT]):
    GROUP_TYPES = [ChatType.GROUP, ChatType.SUPERGROUP]

    def __init__(self, bot: telegram.Bot, api_config: configparser.RawConfigParser):
        super().__init__(self.handle_message)
        self.bot = bot
        telegram_service, user_state_service, admin_service, ics_service, data_access = \
            initialize_services(bot, api_config)
        self.user_state_service = user_state_service
        self.admin_service = admin_service

        self.nodes = self.initialize_nodes(telegram_service, user_state_service, data_access, api_config)

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
        init_node.add_transition('/start', init_node.handle_start)

        rejected_node = RejectedNode(UserState.INIT, telegram_service, user_state_service, data_access)
        rejected_node.add_transition(
            api_config['Chats']['SPECTATOR_PASSWORD'],
            rejected_node.handle_correct_password,
            new_state=UserState.DEFAULT,
            allowed_roles=RoleSet.REJECTED)

        default_node = DefaultNode(UserState.DEFAULT, telegram_service, user_state_service, data_access)
        default_node.add_transition('/website', default_node.handle_website)
        default_node.add_transition('/stats', default_node.handle_stats, new_state=UserState.STATS)
        default_node.add_transition('/edit', default_node.handle_edit, new_state=UserState.EDIT, allowed_roles=RoleSet.PLAYERS)

        stats_node = StatsNode(UserState.STATS, telegram_service, user_state_service, data_access)
        stats_node.add_continue_later()
        stats_node.add_transition('/games', stats_node.handle_games, new_state=UserState.STATS_GAMES)
        stats_node.add_transition('/trainings', stats_node.handle_trainings, new_state=UserState.STATS_TRAININGS)
        stats_node.add_transition('/timekeepings', stats_node.handle_timekeepings, new_state=UserState.STATS_TIMEKEEPINGS)

        stats_games_node = StatsNode(UserState.STATS_GAMES, telegram_service, user_state_service, data_access)
        stats_node.add_continue_later()
        stats_node.add_transition('/game document_id', stats_node.handle_document_id, new_state=UserState.STATS_GAMES)
        stats_node.add_transition('Overview', stats_node.handle_overview, new_state=UserState.STATS)

        stats_trainings_node = StatsNode(UserState.STATS_TRAININGS, telegram_service, user_state_service, data_access)
        stats_trainings_node.add_continue_later()
        stats_trainings_node.add_transition('/game document_id', stats_node.handle_document_id,
                                            new_state=UserState.STATS_TRAININGS)
        stats_trainings_node.add_transition('Overview', stats_node.handle_overview, new_state=UserState.STATS)

        stats_timekeepings_node = StatsNode(UserState.STATS_TIMEKEEPINGS, telegram_service, user_state_service,
                                            data_access)
        stats_timekeepings_node.add_continue_later()
        stats_timekeepings_node.add_transition('/game document_id', stats_node.handle_document_id,
                                               new_state=UserState.STATS_TIMEKEEPINGS)
        stats_timekeepings_node.add_transition('Overview', stats_node.handle_overview, new_state=UserState.STATS)

        return {
            UserState.INIT: init_node,
            UserState.REJECTED: rejected_node,
            UserState.DEFAULT: default_node,
            UserState.STATS: stats_node,
            UserState.STATS_GAMES: stats_games_node,
            UserState.STATS_TRAININGS: stats_trainings_node,
            UserState.STATS_TIMEKEEPINGS: stats_timekeepings_node
        }
