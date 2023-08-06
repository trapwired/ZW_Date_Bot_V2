from telegram import Update

from Enums.MessageType import MessageType
from Enums.PlayerState import PlayerState
from Nodes.Node import Node


class DefaultNode(Node):

    transitions = {
        "/help": [print_help, PlayerState.DEFAULT],
        "/website" : [print_website, PlayerState.DEFAULT]
    }

    async def handle(self, update: Update, player_state: PlayerState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.HELP)

    def print_help(self):
        pass
    

    def print_website(self):
        pass