import configparser

import telegram
from telegram import Update
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT

from src.Enums.PlayerState import PlayerState
from src.Exceptions.ObjectNotFoundException import ObjectNotFoundException
from src.Services.AdminService import AdminService
from src.Services.IcsService import IcsService
from src.Services.PlayerStateService import PlayerStateService
from src.Services.TelegramService import TelegramService
from src.workflows.DefaultWorkflow import DefaultWorkflow
from src.workflows.StartWorkflow import StartWorkflow
from src.workflows.Workflow import Workflow
from src.Data.DataAccess import DataAccess


def initialize_workflows(telegram_service: TelegramService, data_access: DataAccess, player_state_service: PlayerStateService):
    default_workflow = DefaultWorkflow(telegram_service)
    start_workflow = StartWorkflow(telegram_service, data_access, player_state_service)
    return default_workflow, start_workflow, [default_workflow]


class CommandHandler(BaseHandler[Update, CCT]):

    def __init__(self, bot: telegram.Bot, api_config: configparser.RawConfigParser):
        super().__init__(self.handle_message)
        self.bot = bot
        telegram_service, player_state_service, admin_service, ics_service, data_access = self.initialize_services(bot, api_config)
        self.player_state_service = player_state_service
        self.admin_service = admin_service

        default_workflow, start_workflow, all_workflows = initialize_workflows(telegram_service, data_access, player_state_service)
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
                                player_state in wf.valid_states()
                                and command in wf.valid_commands(),
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
            workflow = self.get_applicable_workflow(player_state, command)

        return player_state, workflow
