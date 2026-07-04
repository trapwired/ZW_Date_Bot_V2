from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from features.adminpanel import AdminMenu

from Utils import Format
from Utils import InlineInputStaging


class AnnounceNode(Node):
    """Captures the announcement text an admin types after pressing 'Announce' in the
    admin menu. Each typed value re-renders the admin-menu message with the delivery
    choice (every player privately / group chat); nothing is sent until they choose
    (handled by AdminMenuCallbackNode)."""

    def __init__(self, state, telegram_service, user_state_service, data_access):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.enable_main_menu_escapes(self._clear_pending_announcement)
        self.fallback_action = self.handle_announcement_input

    def _clear_pending_announcement(self, user_to_state: UsersToState) -> None:
        user_to_state.additional_info = ''

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._clear_pending_announcement(user_to_state)
        await self.telegram_service.send_message(
            update=update, all_buttons=None, message='Cancelled - nothing was announced.')

    async def handle_announcement_input(self, update: Update, user_to_state: UsersToState,
                                        new_state: UserState) -> None:
        # Any free text typed in this state is the announcement. Stage it next to the
        # menu-message ids and re-render that message with the delivery choice;
        # retyping just replaces the staged value.
        message_id, chat_id, _ = InlineInputStaging.parse(user_to_state.additional_info)
        announcement = update.message.text.strip()
        user_to_state.additional_info = InlineInputStaging.build(message_id, chat_id, announcement)
        self.user_state_service.update_user_state(user_to_state, self.state)

        message = f'Send this announcement?\n\n{Format.escape(announcement)}'
        markup = AdminMenu.build_announce_confirm_markup()
        if message_id is not None:
            await self.telegram_service.edit_inline_message_text(message, message_id, chat_id, markup)
            # The typed text now lives in the menu message - drop the loose chat message.
            await self.telegram_service.delete_message(update.message.message_id, update.effective_chat.id)
        else:
            # Staged before the menu message was tracked (legacy in-flight flow).
            await self.telegram_service.send_message(
                update=update, all_buttons=None, message=message, reply_markup=markup)
