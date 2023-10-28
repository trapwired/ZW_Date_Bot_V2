from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.CallbackOption import CallbackOption

from databaseEntities.UsersToState import UsersToState

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.UserStateService import UserStateService

from Utils import UpdateEventUtils
from Utils import PrintUtils
from Utils import CallbackUtils


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
        event_summary = PrintUtils.pretty_print(self.event_type)
        pretty_print = UpdateEventUtils.get_inline_message('Adding new', self.event_type, event_summary)
        # TODO add new callbackNode for handling Add-callbacks
        reply_markup = CallbackUtils.get_add_event_reply_markup(UserState.ADMIN_ADD, self.event_type)
        # TODO unclear doc_id? (in get_add_event_reply_markup) + in build_additional_information
        query = await self.telegram_service.send_message(update=update, reply_markup=reply_markup, message=pretty_print)
        # send message, store callback-data in additional data of player
        user_to_state.additional_info = CallbackUtils.build_additional_information(query.message.id,
                                                                                   query.message.chat_id, 'docId44')

        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN_ADD_GAME_TIMESTAMP)

        message = UpdateEventUtils.get_input_format_string(CallbackOption.DATETIME)
        await self.telegram_service.send_message_with_normal_keyboard(update=update, message=message)

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
