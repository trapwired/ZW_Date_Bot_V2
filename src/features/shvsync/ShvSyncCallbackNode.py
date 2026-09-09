from telegram import Update

from Enums import Audience
from Enums.ShvSync import ShvDecisionKind, ShvDecisionStatus
from Enums.UserState import UserState

from framework.Nodes.CallbackNode import CallbackNode

from features.shvsync import SyncMenu

from localization.Translator import t

ALREADY_ANSWERED_TEXT = 'This question was already answered.'
ADOPT_DECLINED_TEXT = 'Okay - I treated them as different games and told the maintainer.'
ASK_REASON_TEXT = 'Okay, skipped. Why not? Send me a short reason for the maintainer (or /cancel).'


class ShvSyncCallbackNode(CallbackNode):
    """Answers to the SHV sync's yes/no questions. Every admin gets the same question,
    so a second press (any admin, either button) must find the decision no longer
    pending and degrade to 'already answered' instead of acting twice. The
    check-then-act below is safe because the application processes updates
    sequentially (no concurrent_updates) - two presses can never interleave."""

    audience = Audience.ADMINS

    def __init__(self, telegram_service, data_access, trigger_service, user_state_service,
                 shv_sync_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.shv_sync_service = shv_sync_service

    async def handle(self, update: Update):
        query = update.callback_query
        await query.answer()

        disable_team_id = SyncMenu.parse_maintainer_disable(query.data)
        if disable_team_id is not None:
            # Maintainer-only: this button rides on a maintainer diagnostic, and a
            # forwarded copy must not let a team admin disable another team's sync.
            if update.effective_chat.id != int(self.telegram_service.maintainer_chat_id):
                return
            self.shv_sync_service.disable_for_team(disable_team_id)
            await self.telegram_service.edit_callback_message(
                query, f'SHV sync disabled for team {disable_team_id}. '
                       f'Re-enable via SQL: shv_sync_disabled = false.')
            return

        parsed = SyncMenu.parse(query.data)
        if parsed is None:
            return
        token, answer = parsed

        decision = self.data_access.find_shv_sync_decision(token)
        if decision is None or decision.status != ShvDecisionStatus.PENDING:
            await self.telegram_service.edit_callback_message(query, t(ALREADY_ANSWERED_TEXT))
            return

        if answer == SyncMenu.YES:
            result_text = await self.shv_sync_service.approve(decision)
            await self.telegram_service.edit_callback_message(query, result_text)
            return

        self.shv_sync_service.decline(decision)
        admin_name = update.effective_user.first_name if update.effective_user else 'an admin'
        await self.shv_sync_service.report_decline_to_maintainer(decision, admin_name)
        if decision.kind == ShvDecisionKind.ADOPT:
            # Spec'd without a reason flow: the pair is final, the maintainer has the data.
            await self.telegram_service.edit_callback_message(query, t(ADOPT_DECLINED_TEXT))
            return

        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        user_to_state.additional_info = decision.token
        self.user_state_service.update_user_state(user_to_state, UserState.SHV_DECLINE_REASON)
        await self.telegram_service.edit_callback_message(query, t(ASK_REASON_TEXT))
