from telegram import Update

from Nodes.Node import Node
from Services.PlayerStateService import PlayerStateService
from Services.TelegramService import TelegramService

from Enums.MessageType import MessageType

from databaseEntities.PlayerToState import PlayerToState


class InitNode(Node):

    # Overwrite handle, because player not yet stored in database
    async def handle(self, update: Update, player_to_state: PlayerToState):
        try:
            command = update.message.text
            transition = self.get_transition(command)
            action = transition.action
            await action(update, player_to_state)

        except Exception as e:
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.ERROR, str(e))

    async def handle_start(self, update: Update, player_to_state: PlayerToState):
        # store in database, maybe even beforehand in handle_help
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)


    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WRONG_START_COMMAND, 'initNode: handle_help')
