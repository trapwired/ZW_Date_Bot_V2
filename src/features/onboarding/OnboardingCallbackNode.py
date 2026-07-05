from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from Enums.Role import Role

from framework.Nodes.CallbackNode import CallbackNode

from features.onboarding import OnboardingMenu

SPECTATOR_TEXT = ("Send me your team's spectator password. You get it from the team "
                  "(an admin sets it in the bot) - just type it here.")
NEW_TEAM_TEXT = ("Add me to your team's Telegram group chat - you need to be an admin "
                 "or the owner of that group. The moment I'm added, I register the team "
                 "and send you a message to finish the setup.")
CHOICE_TEXT = 'There are two ways in - pick one below.'


def _back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('« Back', callback_data=OnboardingMenu.encode(
        OnboardingMenu.HOME))]])


class OnboardingCallbackNode(CallbackNode):
    """Explains the two ways into the bot to a teamless user. Pure message editing -
    the actual joins happen elsewhere (password text on the REJECTED node, adding the
    bot to a group)."""

    required_roles = frozenset({Role.INIT, Role.REJECTED})

    async def handle(self, update: Update):
        query = update.callback_query
        await query.answer()
        action = OnboardingMenu.parse(query.data)

        match action:
            case OnboardingMenu.SPECTATOR:
                await self.telegram_service.edit_callback_message(query, SPECTATOR_TEXT, _back_markup())
            case OnboardingMenu.NEW_TEAM:
                await self.telegram_service.edit_callback_message(query, NEW_TEAM_TEXT, _back_markup())
            case OnboardingMenu.HOME:
                await self.telegram_service.edit_callback_message(
                    query, CHOICE_TEXT, OnboardingMenu.build_choice_markup())
