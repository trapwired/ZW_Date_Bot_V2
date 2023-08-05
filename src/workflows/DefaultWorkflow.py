from telegram import Update

from Enums.MessageType import MessageType
from Enums.PlayerState import PlayerState
from workflows.Workflow import Workflow


class DefaultWorkflow(Workflow):

    def valid_states(self):
        return [PlayerState.DEFAULT]

    async def handle(self, update: Update, player_state: PlayerState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.HELP)

    def valid_commands(self):
        return ['/help']

