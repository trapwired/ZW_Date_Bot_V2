from telegram import Update

from Enums.UserState import UserState

from framework.Nodes.CallbackNode import CallbackNode

from localization.LanguageContext import set_current_language
from localization.Languages import SUPPORTED_LANGUAGES, resolve_user_language
from localization.Translator import t

from features.language import LanguageMenu

PICKER_TEXT = 'Which language should I talk to you in?'
CONFIRMATION_TEXT = 'Language updated 👍'


class LanguageCallbackNode(CallbackNode):
    """Persists the presser's language choice and immediately answers in it: the
    picker message is re-rendered with the new checkmark, and the confirmation
    message carries a freshly localized reply keyboard (reply keyboards only
    change with a new message)."""

    def __init__(self, telegram_service, data_access, trigger_service, user_state_service, node_handler):
        super().__init__(telegram_service, data_access, trigger_service)
        self.user_state_service = user_state_service
        self.node_handler = node_handler

    async def send_picker(self, update: Update, user_to_state, new_state) -> None:
        """The /language transition action - works from any node, state unchanged."""
        current = resolve_user_language(user_to_state.language,
                                        getattr(update.effective_user, 'language_code', None))
        await self.telegram_service.send_message(
            update=update, all_buttons=None, message=t(PICKER_TEXT),
            reply_markup=LanguageMenu.build_picker_markup(current))

    async def handle(self, update: Update):
        query = update.callback_query
        await query.answer()
        action = LanguageMenu.parse(query.data)
        if action == LanguageMenu.PICKER:
            # The 🗣 entry button on a member menu: swap that message for the picker.
            user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
            current = resolve_user_language(user_to_state.language,
                                            getattr(update.effective_user, 'language_code', None))
            await self.telegram_service.edit_callback_message(
                query, t(PICKER_TEXT), LanguageMenu.build_picker_markup(current))
            return
        if action not in SUPPORTED_LANGUAGES:
            return
        language = action
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        self.user_state_service.set_language(user_to_state, language)
        # From here on this update speaks the new language (NodeHandler resolved the
        # old one before this handler ran); its token cleanup still applies.
        set_current_language(language)
        await self.telegram_service.edit_callback_message(
            query, t(PICKER_TEXT), LanguageMenu.build_picker_markup(language))
        default_node = self.node_handler.get_node(UserState.DEFAULT)
        await self.telegram_service.send_message(
            update=update, all_buttons=default_node.get_commands_for_buttons(user_to_state, None),
            message=t(CONFIRMATION_TEXT))
