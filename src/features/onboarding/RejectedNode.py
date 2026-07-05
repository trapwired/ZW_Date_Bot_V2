from telegram import Update

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from framework.Nodes.Node import Node

from domain import SpectatorPasswordPolicy
from domain.entities.UsersToState import UsersToState

from features.onboarding import OnboardingMenu
from features.onboarding import SpectatorOnboarding

from Utils import DateTimeUtils

LOCKED_OUT_TEXT = 'Too many attempts - please try again tomorrow.'


class RejectedNode(Node):

    def __init__(self, state, telegram_service, user_state_service, data_access, team_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.team_service = team_service
        # Free text on the REJECTED screen is a spectator-password attempt.
        self.fallback_action = self.handle_password_attempt

    async def handle_password_attempt(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # A '/start <token>' here is an invite deep link pressed while REJECTED - it is
        # not a password guess, so it neither burns throttle attempts nor records one.
        token = SpectatorOnboarding.extract_start_token(update.message.text)
        if token is not None:
            team = self.team_service.redeem_spectator_invite(token)
            if team is None:
                await self.handle_help(update, user_to_state, new_state)
                return
            await SpectatorOnboarding.join_as_spectator(self, update, user_to_state, team)
            return

        now = DateTimeUtils.get_local_now()
        attempts = SpectatorPasswordPolicy.decode(user_to_state.additional_info)
        if SpectatorPasswordPolicy.is_locked(attempts, now):
            await self.telegram_service.send_message(update=update, all_buttons=None, message=LOCKED_OUT_TEXT)
            return

        # The password identifies the team (unique across teams); matching is exact and
        # case-sensitive on the raw text.
        team = self.team_service.find_team_by_spectator_password(update.message.text.strip())
        if team is None:
            await self._register_failed_attempt(update, user_to_state, attempts, now)
            # Same generic rejection as any other text - a guesser gets no signal that
            # they are talking to a password prompt.
            await self.handle_help(update, user_to_state, new_state)
            return

        await SpectatorOnboarding.join_as_spectator(self, update, user_to_state, team)

    async def _register_failed_attempt(self, update: Update, user_to_state: UsersToState, attempts, now):
        record = SpectatorPasswordPolicy.register_failure(attempts, now)
        user_to_state.additional_info = SpectatorPasswordPolicy.encode(record)
        self.user_state_service.update_user_state(user_to_state, UserState.REJECTED)
        if SpectatorPasswordPolicy.just_reached_lockout(record):
            await self.telegram_service.send_maintainer_message(
                f'Spectator-password lockout: user {update.effective_chat.id} failed '
                f'{record.failed_count} attempts within the window')

    async def handle_help(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message_type=MessageType.REJECTED,
            reply_markup=OnboardingMenu.build_choice_markup())
