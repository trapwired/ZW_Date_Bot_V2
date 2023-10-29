from telegram import Update, CallbackQuery

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils
from Utils import PrintUtils

from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.MessageType import MessageType

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.UserStateService import UserStateService

from Utils import UpdateEventUtils

from Nodes.AdminNode import AdminNode


# TODO organize imports, as soon as finished


class AddEventCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 node_handler, user_state_service: UserStateService):
        super().__init__(telegram_service, data_access, trigger_service)
        self.node_handler = node_handler
        self.user_state_service = user_state_service

    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, callback_option, _ = CallbackUtils.try_parse_callback_message(query.data)

        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)

        match callback_option:
            case CallbackOption.CANCEL:
                await update.callback_query.answer()
                user_to_state.additional_info = ''
                self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)
                admin_node = self.node_handler.get_node(UserState.ADMIN)
                await self.telegram_service.send_message(
                    update=update,
                    all_buttons=admin_node.get_commands_for_buttons(user_to_state.role, UserState.ADMIN,
                                                                         update.effective_chat.id),
                    message_type=MessageType.ADMIN)
                await self.telegram_service.delete_message(update)
                await self.telegram_service.delete_next_message(update)
            case CallbackOption.RESTART:
                await update.callback_query.answer()
                await update.callback_query.delete_message()
                admin_add_node = self.node_handler.get_node(UserState.ADMIN_ADD)
                await admin_add_node.handle_add_game(update, user_to_state, UserState.ADMIN_ADD_GAME)
