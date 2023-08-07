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
from workflows.DefaultWorkflow import DefaultWorkflow
from workflows.StartWorkflow import StartWorkflow
from workflows.Workflow import Workflow
from Data.DataAccess import DataAccess


def initialize_workflows(telegram_service: TelegramService, data_access: DataAccess,
                         player_state_service: PlayerStateService):
    default_workflow = DefaultWorkflow(telegram_service)
    start_workflow = StartWorkflow(telegram_service, data_access, player_state_service)
    all_workflows = [default_workflow]
    return default_workflow, start_workflow, all_workflows


class CommandHandler(BaseHandler[Update, CCT]):

    def __init__(self, bot: telegram.Bot, api_config: configparser.RawConfigParser):
        super().__init__(self.handle_message)
        self.bot = bot
        telegram_service, player_state_service, admin_service, ics_service, data_access = self.initialize_services(bot,
                                                                                                                   api_config)
        self.player_state_service = player_state_service
        self.admin_service = admin_service

        default_workflow, start_workflow, all_workflows = initialize_workflows(telegram_service, data_access,
                                                                               player_state_service)
        self.start_workflow = start_workflow
        self.default_workflow = default_workflow
        self.workflows = all_workflows

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text:
            return

        player_state, workflow = self.get_playerstate_and_workflow(update)
        await workflow.handle(update, player_state)

    def get_applicable_workflow(self, player_state: PlayerState, command: str) -> Workflow:
        workflows = list(filter(lambda wf:
                                player_state in wf.valid_states(),
                                self.workflows))
        if len(workflows) == 0:
            # TODO tryParse Game/TKE/Training
            # if successful:
            workflows = list(filter(lambda wf:
                                    player_state in wf.valid_states()
                                    and wf.supports_string_commands,
                                    self.workflows))
            # second attribute for workflows: accept wild strings
            pass
        if len(workflows) == 1:
            return workflows[0]
        # default
        return self.default_workflow

    def initialize_services(self, bot: telegram.Bot, api_config: configparser.RawConfigParser):
        data_access = DataAccess(api_config)
        telegram_service = TelegramService(bot)
        player_state_service = PlayerStateService(data_access)
        admin_service = AdminService(data_access)
        ics_service = IcsService(data_access)
        return telegram_service, player_state_service, admin_service, ics_service, data_access

    def get_playerstate_and_workflow(self, update):
        telegram_id = update.effective_chat.id
        try:
            player_state = self.player_state_service.get_player_state(telegram_id)
        except ObjectNotFoundException:
            # player not present
            workflow = self.start_workflow
            player_state = None
        else:
            command = update.message.text
            workflow = self.get_workflow(player_state, command)

        dict = {
            PlayerState.INIT: InitNode(telegramService, DataAccess, transitions=
            {
                '/start': Transition(self.handle_start, PlayerState.DEFAULT),
                'default': Transition(self.handle_else, PlayerState.INIT)}),
            PlayerState.DEFAULT: DefaultNode(telegramService, DataAccess, transitions=
            {
                '/help': Transition(self.handle_help, PlayerState.DEFAULT),
                '/website': Transition(self.handle_website, PlayerState.DEFAULT),
                '/stats': Transition(self.handle_stats, PlayerState.STATS),
                '/edit': Transition(self.handle_edit, PlayerState.EDIT),
            }),
            PlayerState.STATS: StatsNode(telegramService, DataAccess, transitions=
            {
                '/games': Transition(self.handle_games, PlayerState.STATS_GAMES),
                '/trainings': Transition(self.handle_trainings, PlayerState.STATS_TRAINING),
                '/timekeepings': Transition(self.handle_timekeepings, PlayerState.TIMEKEEPING),
                'continue later': Transition(self.handle_continueLater, PlayerState.DEFAULT)
            }),
            PlayerState.STATS_GAMES: StatsNode(telegramService, DataAccess, transitions=
            {
                '/game document_id': Transition(self.handle_documentId, PlayerState.STATS_GAMES),
                'back to stats': Transition(self.handle_backToStats, PlayerState.STATS),
                'continue later': Transition(self.handle_continueLater, PlayerState.DEFAULT),
            }),
            PlayerState.STATS_TRAININGS: StatsNode(telegramService, DataAccess, transitions=
            {

                '/training document_id': Transition(self.handle_documentId, PlayerState.STATS_TRAINING),
                'back to stats': Transition(self.handle_backToStats, PlayerState.STATS),
                'continue later': Transition(self.handle_continueLater, PlayerState.DEFAULT),
            }),
            PlayerState.STATS_TIMEKEEPINGS: StatsNode(telegramService, DataAccess, transitions=
            {

                '/tke document_id': Transition(self.handle_documentId, PlayerState.STATS_TIMEKEEPING),
                'back to stats': Transition(self.handle_backToStats, PlayerState.STATS),
                'continue later': Transition(self.handle_continueLater, PlayerState.DEFAULT),
            }),

        }
        return player_state, workflow
