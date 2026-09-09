from telegram import Update

from Enums.UserState import UserState

from framework.Nodes.Node import Node

from domain.entities.UsersToState import UsersToState

from localization.Translator import t

CANCELLED_TEXT = 'Okay, no reason recorded.'
THANKS_TEXT = 'Thanks, passed it on 👍'


class DeclineReasonNode(Node):
    """Captures the free-text reason after an admin declined an SHV sync question.
    The declined decision's token sits in additional_info; the decline itself is
    already recorded and reported, so cancelling here loses only the reason."""

    def __init__(self, state, telegram_service, user_state_service, data_access, shv_sync_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.shv_sync_service = shv_sync_service
        self.add_transition('/cancel', self.handle_cancel, new_state=UserState.DEFAULT)
        self.enable_main_menu_escapes(self._clear_context)
        self.fallback_action = self.handle_reason

    def _clear_context(self, user_to_state: UsersToState) -> None:
        user_to_state.additional_info = ''

    async def handle_cancel(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        self._clear_context(user_to_state)
        await self.telegram_service.send_message(update=update, all_buttons=None,
                                                 message=t(CANCELLED_TEXT))

    async def handle_reason(self, update: Update, user_to_state: UsersToState,
                            new_state: UserState) -> None:
        reason = update.message.text.strip()
        decision = self.data_access.find_shv_sync_decision(user_to_state.additional_info)
        if decision is not None:
            self.shv_sync_service.record_decline_reason(decision, reason)
            await self.shv_sync_service.report_decline_reason_to_maintainer(decision)
        else:
            # The decision was cleaned up in the meantime (a sync ran and its subject
            # changed) - the typed reason must still reach the maintainer, not vanish.
            await self.telegram_service.send_maintainer_message(
                f'SHV sync: reason for an already-resolved question - {reason}')
        user_to_state.additional_info = ''
        self.user_state_service.update_user_state(user_to_state, UserState.DEFAULT)
        await self.telegram_service.send_message(update=update, all_buttons=None,
                                                 message=t(THANKS_TEXT))
