import configparser

import telegram
from telegram import Update
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT

from Enums.PlayerState import PlayerState
from Exceptions.ObjectNotFoundException import ObjectNotFoundException
from Services.AdminService import AdminService
from Services.IcsService import IcsService
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService
from src.Nodes.DefaultNode import DefaultNode
from src.Nodes.InitNode import InitNode
from src.Nodes.Node import Node
from src.Nodes.StatsNode import StatsNode
from src.Nodes.Transition import Transition
from workflows.DefaultWorkflow import DefaultWorkflow
from workflows.StartWorkflow import StartWorkflow
from workflows.Workflow import Workflow
from Data.DataAccess import DataAccess


def initialize_services(bot: telegram.Bot, api_config: configparser.RawConfigParser):
    data_access = DataAccess(api_config)
    telegram_service = TelegramService(bot)
    player_state_service = PlayerStateService(data_access)
    admin_service = AdminService(data_access)
    ics_service = IcsService(data_access)
    return telegram_service, player_state_service, admin_service, ics_service, data_access


class NodeHandler(BaseHandler[Update, CCT]):

    def __init__(self, bot: telegram.Bot, api_config: configparser.RawConfigParser):
        super().__init__(self.handle_message)
        self.bot = bot
        telegram_service, player_state_service, admin_service, ics_service, data_access = initialize_services(bot,
                                                                                                              api_config)
        self.player_state_service = player_state_service
        self.admin_service = admin_service

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text:
            return

        player_state, workflow = self.get_playerstate_and_workflow(update)
        await workflow.handle(update, player_state)

    def get_node(self, player_state: PlayerState, command: str) -> Node:
        pass

    def initialize_nodes(self, telegram_service: TelegramService, player_state_service: PlayerStateService,
                         data_access: DataAccess):

        init_node = InitNode(PlayerState.INIT, telegram_service, player_state_service, data_access)
        init_node.add_transition('/start', init_node.handle_start, PlayerState.DEFAULT)

        default_node = DefaultNode(PlayerState.DEFAULT, telegram_service, player_state_service, data_access)
        default_node.add_transition('/website', default_node.handle_website)
        default_node.add_transition('/stats', default_node.handle_stats)
        default_node.add_transition('/edit', default_node.handle_edit)

        stats_node = StatsNode(PlayerState.STATS, telegram_service, player_state_service, data_access)
        stats_node.add_continue_later()
        stats_node.add_transition('/games', stats_node.handle_games, PlayerState.STATS_GAMES)
        stats_node.add_transition('/trainings', stats_node.handle_trainings, PlayerState.STATS_TRAININGS)
        stats_node.add_transition('/timekeepings', stats_node.handle_timekeepings, PlayerState.STATS_TIMEKEEPINGS)

        stats_games_node = StatsNode(PlayerState.STATS_GAMES, telegram_service, player_state_service, data_access)
        stats_node.add_continue_later()
        stats_node.add_transition('/game document_id', stats_node.handle_document_id, PlayerState.STATS_GAMES)
        stats_node.add_transition('Overview', stats_node.handle_overview, PlayerState.STATS)

        stats_trainings_node = StatsNode(PlayerState.STATS_TRAININGS, telegram_service, player_state_service,
                                         data_access)
        stats_trainings_node.add_continue_later()
        stats_trainings_node.add_transition('/game document_id', stats_node.handle_document_id,
                                            PlayerState.STATS_TRAININGS)
        stats_trainings_node.add_transition('Overview', stats_node.handle_overview, PlayerState.STATS)

        stats_timekeepings_node = StatsNode(PlayerState.STATS_TIMEKEEPINGS, telegram_service, player_state_service,
                                            data_access)
        stats_timekeepings_node.add_continue_later()
        stats_timekeepings_node.add_transition('/game document_id', stats_node.handle_document_id,
                                               PlayerState.STATS_TIMEKEEPINGS)
        stats_timekeepings_node.add_transition('Overview', stats_node.handle_overview, PlayerState.STATS)

        return {
            PlayerState.INIT: init_node,
            PlayerState.DEFAULT: default_node,
            PlayerState.STATS: stats_node,
            PlayerState.STATS_GAMES: stats_games_node,
            PlayerState.STATS_TRAININGS: stats_trainings_node,
            PlayerState.STATS_TIMEKEEPINGS: stats_timekeepings_node
        }
