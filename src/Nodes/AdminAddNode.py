from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService


class AdminAddNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_type: Event, node_handler):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_type = event_type
        self.add_cancel_transition()
        self.node_handler = node_handler

    def add_cancel_transition(self):
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.ADMIN)

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # TODO correctly reset everything
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_add_game(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # assemble callback message
        # Create empty Event (date XXX?)

        # pretty print: New Game: XX.XX.XXXX | XXX | XXX

        # Add buttons: restart, cancel
        # send message, store callback-data in additional data of player

        # send format information message + always cancel via /cancel
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)

    async def handle_add_training(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)

    async def handle_add_timekeeping(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)

    async def handle_user_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # Switch on self.state
        # tryparse date or string
        # how to update user_state?
        # always resend callback (if so, delete old one)
        # send format / expcted + always /cancel
        pass

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # use default transition for anything that can't be predicted
        await self.handle_user_input(update, user_to_state, new_state)
