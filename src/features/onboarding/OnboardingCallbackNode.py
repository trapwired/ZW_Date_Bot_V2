from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from Enums.MessageType import MessageType
from Enums.Role import Role
from Enums.UserState import UserState

from framework.Nodes.CallbackNode import CallbackNode
from framework.Services.TelegramService import get_text

from localization.Translator import t

from features.onboarding import OnboardingMenu

SPECTATOR_TEXT = ("Send me your team's spectator password. You get it from the team "
                  "(an admin sets it in the bot) - just type it here.")
NEW_TEAM_TEXT = ("Add me to your team's Telegram group chat - you need to be an admin "
                 "or the owner of that group. The moment I'm added, I register the team "
                 "and send you a message to finish the setup.")


def _back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(t('« Back'), callback_data=OnboardingMenu.encode(
        OnboardingMenu.HOME))]])


class OnboardingCallbackNode(CallbackNode):
    """Explains the two ways into the bot to a teamless user. The spectator choice
    parks the presser in the REJECTED state so their next text lands in the
    password fallback; everything else is pure message editing."""

    required_roles = frozenset({Role.INIT, Role.REJECTED})

    def __init__(self, telegram_service, data_access, trigger_service, user_state_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service

    async def handle(self, update: Update):
        query = update.callback_query
        await query.answer()
        action = OnboardingMenu.parse(query.data)

        match action:
            case OnboardingMenu.SPECTATOR:
                # A rolled-back user is INIT again; only the REJECTED node treats free
                # text as a password attempt, so park them there before they type.
                user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
                if user_to_state.state is not UserState.REJECTED:
                    self.user_state_service.update_user_state(user_to_state, UserState.REJECTED)
                await self.telegram_service.edit_callback_message(query, t(SPECTATOR_TEXT), _back_markup())
            case OnboardingMenu.NEW_TEAM:
                await self.telegram_service.edit_callback_message(query, t(NEW_TEAM_TEXT), _back_markup())
            case _:
                # HOME and any unknown/retired ONB action land on the choice screen -
                # same copy as the initial rejection message, one source, no drift.
                message = get_text(MessageType.REJECTED, first_name=update.effective_user.first_name)
                await self.telegram_service.edit_callback_message(
                    query, message, OnboardingMenu.build_choice_markup())
