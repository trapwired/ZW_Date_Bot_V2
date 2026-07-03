from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from framework.Services.TeamService import TeamService

from features.adminpanel import AdminMenu

from Utils import Format
from Utils import InlineInputStaging


class UpdateSpectatorPasswordNode(Node):
    """Captures the new spectator password an admin types after pressing 'Spectator
    password' in the admin menu. Each typed value re-renders the admin-menu message with
    Save/Cancel; nothing is persisted until Save (handled by AdminMenuCallbackNode)."""

    def __init__(self, state, telegram_service, user_state_service, data_access, team_service: TeamService):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.team_service = team_service
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.enable_main_menu_escapes(self._clear_pending_password)
        self.fallback_action = self.handle_password_input

    def _clear_pending_password(self, user_to_state: UsersToState) -> None:
        user_to_state.additional_info = ''

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._clear_pending_password(user_to_state)
        await self.telegram_service.send_message(
            update=update, all_buttons=None, message='Cancelled - the spectator password was not changed.')

    async def handle_password_input(self, update: Update, user_to_state: UsersToState, new_state: UserState) -> None:
        # Any free text typed in this state is the new spectator password. Stage it next
        # to the menu-message ids (it doesn't fit in callback_data) and re-render that
        # message with Save/Cancel; retyping just replaces the staged value.
        message_id, chat_id, _ = InlineInputStaging.parse(user_to_state.additional_info)
        new_password = update.message.text.strip()
        user_to_state.additional_info = InlineInputStaging.build(message_id, chat_id, new_password)
        self.user_state_service.update_user_state(user_to_state, self.state)

        message = f'Set the spectator password to:\n{Format.escape(new_password)}\n\nSave it?'
        markup = AdminMenu.build_spectator_password_confirm_markup()
        if message_id is not None:
            await self.telegram_service.edit_inline_message_text(message, message_id, chat_id, markup)
            # The typed password now lives in the menu message - drop the loose chat message.
            await self.telegram_service.delete_message(update.message.message_id, update.effective_chat.id)
        else:
            # Staged before the menu message was tracked (legacy in-flight flow).
            await self.telegram_service.send_message(
                update=update, all_buttons=None, message=message, reply_markup=markup)
