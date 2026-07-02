from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from features.adminpanel import AdminMenu


class UpdateWebsiteNode(Node):
    """Captures the new website URL an admin types after pressing 'Set website' in the
    admin menu; the yes/no confirmation buttons are handled by AdminMenuCallbackNode."""

    def __init__(self, state, telegram_service, user_state_service, data_access):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.enable_main_menu_escapes(self._clear_pending_url)
        self.fallback_action = self.handle_url_input

    def _clear_pending_url(self, user_to_state: UsersToState) -> None:
        user_to_state.additional_info = ''

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._clear_pending_url(user_to_state)
        await self.telegram_service.send_message(
            update=update, all_buttons=None, message='Cancelled - the website link was not changed.')

    async def handle_url_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
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
            reply_markup=AdminMenu.build_website_confirm_markup())
