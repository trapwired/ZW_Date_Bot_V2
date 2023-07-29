import telegram
from telegram import Update
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT

from src.States.PlayerState import PlayerState
from src.workflows.DefaultWorkflow import DefaultWorkflow
from src.workflows.Workflow import Workflow


def initialize_workflows(bot: telegram.Bot):
    return [DefaultWorkflow(bot)]


class CommandHandler(BaseHandler[Update, CCT]):
    __slots__ = ("commands", "filters", "bot", "workflows")

    # playerStateService
    # AdminService

    def __init__(self, bot: telegram.Bot):
        super().__init__(self.handle_message)
        self.bot = bot
        self.workflows = initialize_workflows(bot)

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text:
            return

        player_state = PlayerState.INIT
        command = update.message.text

        workflow = self.get_applicable_workflow(player_state, command)
        await workflow.handle(update)

    def get_applicable_workflow(self, player_state: PlayerState, command: str) -> Workflow:
        workflows = list(filter(lambda wf:
                                player_state in wf.valid_states()
                                and command in wf.valid_commands(),
                                self.workflows))
        if len(workflows) == 0:
            return self.workflows[0]
        # TODO access default workflow
        return workflows[0]
        # TODO make sure its only one
