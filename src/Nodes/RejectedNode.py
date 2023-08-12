from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role

from databaseEntities.PlayerToState import PlayerToState
from Nodes.Node import Node


class RejectedNode(Node):

    async def handle_correct_password(self, update: Update, player_to_state: PlayerToState):
        player_to_state = player_to_state.add_role(Role.SPECTATOR)
        self.data_access.update(player_to_state)
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)

    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED)
