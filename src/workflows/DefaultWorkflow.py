import telegram
from telegram import Update

from src.States.PlayerState import PlayerState
from src.workflows.Workflow import Workflow


class DefaultWorkflow(Workflow):

    def valid_states(self):
        return [PlayerState.DEFAULT]

    async def handle(self, update: Update):
        await self.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

    def valid_commands(self):
        return ['/help']

