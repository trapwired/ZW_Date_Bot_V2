from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.UserStateService import UserStateService

from Data.DataAccess import DataAccess

from Enums.CallbackOption import CallbackOption
from Enums.MessageType import MessageType
from Enums.RoleSet import RoleSet
from Enums.UserState import UserState

from Utils import CallbackUtils


class UpdateWebsiteCallbackNode(CallbackNode):
    required_roles = RoleSet.ADMINS

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 user_state_service: UserStateService, node_handler, website_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.node_handler = node_handler
        self.website_service = website_service

    async def handle(self, update: Update):
        query = update.callback_query
        _, _, callback_option, _ = CallbackUtils.try_parse_callback_message(query.data)

        await query.answer()

        telegram_id = query.from_user.id

        match callback_option:
            case CallbackOption.YES:
                new_url, user_to_state = self.website_service.commit_pending_url(telegram_id)
                message = f'✅ The website link was updated to:\n{new_url}'
            case CallbackOption.NO:
                user_to_state = self.website_service.discard_pending_url(telegram_id)
                message = 'Cancelled - the website link was not changed.'
            case _:
                return

        self.user_state_service.update_user_state(user_to_state, UserState.ADMIN)
        await self.telegram_service.edit_callback_message(query, message)

        # The admin left the admin menu to type the URL, so re-render it with the correct keyboard.
        # The callback's chat is the admin's DM, so `update` carries the right recipient.
        admin_node = self.node_handler.get_node(UserState.ADMIN)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=admin_node.get_commands_for_buttons(user_to_state.role, UserState.ADMIN, telegram_id),
            message_type=MessageType.ADMIN)
