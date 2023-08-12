from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.PlayerState import PlayerState
from Enums.Role import Role

from databaseEntities.PlayerToState import PlayerToState
from databaseEntities.Player import Player

from Exceptions.ObjectNotFoundException import ObjectNotFoundException


def create_player(update: Update) -> Player:
    return Player(update.effective_chat.id, update.effective_user.first_name, update.effective_user.last_name)


class InitNode(Node):

    # Override to add new player
    async def handle(self, update: Update, player_to_state: PlayerToState):
        telegram_id = update.effective_chat.id
        try:
            player_to_state = self.player_state_service.get_player_state(telegram_id)
        except ObjectNotFoundException:
            player = create_player(update)
            player_to_state = self.data_access.add(player)
        await super().handle(update, player_to_state)

    async def handle_start(self, update: Update, player_to_state: PlayerToState):
        telegram_id = update.effective_chat.id
        if self.is_player(telegram_id):
            player_to_state = player_to_state.add_role(Role.PLAYER)
            self.player_state_service.update_player_state(player_to_state, PlayerState.DEFAULT)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.WELCOME)
            await self.telegram_service.send_message(
                update.effective_chat.id,
                MessageType.HELP,
                keyboard_btn_list=self.generate_keyboard())
        else:
            player_to_state = player_to_state.add_role(Role.REJECTED)
            self.player_state_service.update_player_state(player_to_state, PlayerState.REJECTED)
            await self.telegram_service.send_message(update.effective_chat.id, MessageType.REJECTED)

    def is_player(self, telegram_id: int):
        # is person member of group chat
        return False

    async def handle_help(self, update: Update, player_to_state: PlayerToState):
        await self.telegram_service.send_message(update.effective_chat.id, MessageType.WRONG_START_COMMAND)
