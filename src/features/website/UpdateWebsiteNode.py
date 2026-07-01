from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState
from Enums.MessageType import MessageType

from databaseEntities.UsersToState import UsersToState

from Utils import CallbackUtils


class UpdateWebsiteNode(Node):
    def __init__(self, state, telegram_service, user_state_service, data_access):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.add_continue_later()
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.ADMIN)

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, new_state)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADMIN)

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # Any free text typed in this state is the new website URL. Stash it in the user's state so the
        # confirm callback can read it back (it doesn't fit in callback_data), and show a yes/no confirm.
        new_url = update.message.text.strip()
        user_to_state.additional_info = new_url
        self.user_state_service.update_user_state(user_to_state, self.state)
        message = f'Set the website link to:\n{new_url}\n\nIs that correct?'
        await self.telegram_service.send_message(
            update=update,
            all_buttons=None,
            message=message,
            reply_markup=CallbackUtils.get_website_confirm_markup())
