from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from features.adminpanel import AdminMenu
from features.website.WebsiteService import WebsiteService

from Utils import Format


class UpdateWebsiteNode(Node):
    """Captures the new website URL an admin types after pressing 'Set website' in the
    admin menu. Each typed URL re-renders the admin-menu message with Save/Cancel;
    nothing is persisted until Save (handled by AdminMenuCallbackNode)."""

    def __init__(self, state, telegram_service, user_state_service, data_access, website_service: WebsiteService):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.website_service = website_service
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
        # Any free text typed in this state is the new website URL. Stage it next to the
        # menu-message ids (it doesn't fit in callback_data) and re-render that message
        # with Save/Cancel; retyping just replaces the staged value.
        message_id, chat_id, _ = self.website_service.parse_pending(user_to_state.additional_info)
        new_url = update.message.text.strip()
        user_to_state.additional_info = self.website_service.build_pending(message_id, chat_id, new_url)
        self.user_state_service.update_user_state(user_to_state, self.state)

        message = f'Set the website link to:\n{Format.escape(new_url)}\n\nSave it?'
        markup = AdminMenu.build_website_confirm_markup()
        if message_id is not None:
            await self.telegram_service.edit_inline_message_text(message, message_id, chat_id, markup)
            # The typed URL now lives in the menu message - drop the loose chat message.
            await self.telegram_service.delete_message(update.message.message_id, update.effective_chat.id)
        else:
            # Staged before the menu message was tracked (legacy in-flight flow).
            await self.telegram_service.send_message(
                update=update, all_buttons=None, message=message, reply_markup=markup)
