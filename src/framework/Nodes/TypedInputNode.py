from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState

from domain.entities.UsersToState import UsersToState

from Utils import InlineInputStaging


class TypedInputNode(Node):
    """Skeleton for the admin typed-input flows (website URL, spectator password,
    announcement). Free text is staged in additional_info next to the menu-message
    ids, and that menu message re-renders with the subclass's confirm markup;
    nothing is persisted or sent until a confirm button is pressed (handled by
    AdminMenuCallbackNode). Subclasses supply the texts and may reject a value."""

    cancelled_text = 'Cancelled.'

    def __init__(self, state, telegram_service, user_state_service, data_access):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.enable_main_menu_escapes(self._clear_staged_value)
        self.fallback_action = self.handle_typed_value

    def confirm_text(self, value: str) -> str:
        raise NotImplementedError

    def confirm_markup(self):
        raise NotImplementedError

    def review_value(self, value: str) -> tuple[str, object] | None:
        """Reject a typed value: return the (message, markup) to show WITHOUT staging
        it - a rejected value must never sit behind the confirm buttons. None accepts."""
        return None

    def _clear_staged_value(self, user_to_state: UsersToState) -> None:
        user_to_state.additional_info = ''

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._clear_staged_value(user_to_state)
        await self.telegram_service.send_message(update=update, all_buttons=None, message=self.cancelled_text)

    async def handle_typed_value(self, update: Update, user_to_state: UsersToState,
                                 new_state: UserState) -> None:
        # Any free text typed in this state is the value; retyping replaces it.
        message_id, chat_id, _ = InlineInputStaging.parse(user_to_state.additional_info)
        value = update.message.text.strip()

        rejection = self.review_value(value)
        if rejection is not None:
            message, markup = rejection
        else:
            user_to_state.additional_info = InlineInputStaging.build(message_id, chat_id, value)
            self.user_state_service.update_user_state(user_to_state, self.state)
            message, markup = self.confirm_text(value), self.confirm_markup()

        if message_id is not None:
            await self.telegram_service.edit_inline_message_text(message, message_id, chat_id, markup)
            # The typed value now lives in the menu message - drop the loose chat message.
            await self.telegram_service.delete_message(update.message.message_id, update.effective_chat.id)
        else:
            # Staged before the menu message was tracked (legacy in-flight flow).
            await self.telegram_service.send_message(
                update=update, all_buttons=None, message=message, reply_markup=markup)
