from Data.DataAccess import DataAccess

from Enums.CallbackOption import CallbackOption
from Enums.MessageType import MessageType
from Enums.UserState import UserState

from Nodes.CallbackNode import CallbackNode

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.UserStateService import UserStateService

from Utils import CallbackUtils

from telegram import Update


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
        temp_data = self.data_access.get_temp_data(user_to_state.user_id)

        match callback_option:
            case CallbackOption.CANCEL:
                await update.callback_query.answer()

                self.data_access.delete(temp_data)

                admin_node = self.node_handler.get_node(UserState.ADMIN)
                sent_message = await self.telegram_service.send_message(
                    update=update,
                    all_buttons=admin_node.get_commands_for_buttons(user_to_state.role, UserState.ADMIN,
                                                                    update.effective_chat.id),
                    message_type=MessageType.ADMIN)

                self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)

                await self.telegram_service.delete_message(update)
                await self.telegram_service.delete_previous_message(sent_message)
                return

            case CallbackOption.RESTART:
                await update.callback_query.answer()

                self.data_access.delete(temp_data)

                message = 'Sure, let\'s restart...'
                sent_message = await self.telegram_service.send_message_with_normal_keyboard(update, message)

                await update.callback_query.delete_message()
                await self.telegram_service.delete_previous_message(sent_message)

                admin_add_node = self.node_handler.get_node(UserState.ADMIN_ADD)
                await admin_add_node.handle_add_game(update, user_to_state, UserState.ADMIN_ADD_GAME)
                return

            case CallbackOption.SAVE:
                # TODO
                return
