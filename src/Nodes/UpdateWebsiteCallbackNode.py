from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.UserStateService import UserStateService

from Data.DataAccess import DataAccess

from Enums.CallbackOption import CallbackOption
from Enums.MessageType import MessageType
from Enums.UserState import UserState

from Utils import CallbackUtils


class UpdateWebsiteCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, node_handler):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.node_handler = node_handler

    async def handle(self, update: Update):
        query = update.callback_query
        _, _, callback_option, _ = CallbackUtils.try_parse_callback_message(query.data)

        await query.answer()

        telegram_id = query.from_user.id
        user_to_state = self.data_access.get_user_state(telegram_id)

        match callback_option:
            case CallbackOption.YES:
                new_url = user_to_state.additional_info
                self.data_access.set_website(new_url)
                message = f'✅ The website link was updated to:\n{new_url}'
            case CallbackOption.NO:
                message = 'Cancelled - the website link was not changed.'
            case _:
                return

        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)
        await self.telegram_service.edit_callback_message(query, message)

        # The admin left the admin menu to type the URL, so re-render it with the correct keyboard.
        admin = self.data_access.get_user(telegram_id)
        admin_node = self.node_handler.get_node(UserState.ADMIN)
        await self.telegram_service.send_message(
            update=admin,
            all_buttons=admin_node.get_commands_for_buttons(user_to_state.role, UserState.ADMIN, telegram_id),
            message_type=MessageType.ADMIN)
