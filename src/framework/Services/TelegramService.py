import logging
import traceback

import telegram
from multipledispatch import dispatch
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup

from Enums.MessageType import MessageType
from Enums.Event import Event

from Utils import PrintUtils
from Utils import Format
from Utils.ApiConfig import ApiConfig

from domain.entities.TelegramUser import TelegramUser
from telegram.error import BadRequest, Forbidden

from Utils.CustomExceptions import ExpectedException

from framework.Services.UserStateService import UserStateService


def get_text(message_type: MessageType, extra_text: str = '', first_name: str = ''):
    match message_type:
        case MessageType.ERROR:
            return 'Something went wrong - please try again, the maintainer has been notified :)'
        case MessageType.WRONG_START_COMMAND:
            return 'Please start chatting with me by sending the command /start'
        case MessageType.WELCOME:
            return 'Hi ' + Format.escape(first_name) + ', welcome to the ' + Format.bold('Züri West manager') + ' 👋'
        case MessageType.WEBSITE:
            return 'Here you go :)'
        case MessageType.PRIVACY:
            return ("Privacy Policy\n\n"
                    "Hey there! I'm your friendly neighborhood Telegram bot, and I'm here to help manage your team's "
                    "attendance for games, trainings, and timekeeping events. But first, let's talk about privacy.\n\n"
                    "You see, even though I'm a bot, I respect your privacy just like any good friend would. "
                    "Here's what I keep in my digital notebook:\n"
                    "- Your first and last name, as you've shared in your profile,\n"
                    "- Your unique chatId that Telegram gave you,\n"
                    "- Your attendance status (YES, NO, or UNSURE) for past and future trainings, games, "
                    "and timekeeping events."
                    "Don't worry, I only know what you tell me!\n\n"
                    "Now, where do I keep this information? In a top-notch, secure-as-a-fortress database, "
                    "protected by a password and 2FA. Your personal details (name and chatId) have their own VIP table,"
                    " and all other information is linked via randomly generated IDs.\n\n"
                    "I'm not a blabbermouth, so your data stays with me indefinitely and is only accessible by my "
                    "creator, the sole maintainer of this bot. I promise, your data is never sold, traded, or given "
                    "away to any other folks or legal entities.\n\n"
                    "So, that's it! Now let's get back to managing your team's schedule, shall we?")
        case MessageType.REJECTED:
            return 'I am sorry, you are not allowed to use this bot. If you think this is wrong, contact the person ' \
                   'you got the bot recommended from... :)'

        case MessageType.ENROLLMENT_REMINDER:
            return 'Hey ' + Format.escape(first_name) + (', please quickly take your time to update your attendance '
                                                         'for the following upcoming event(s):')

        case MessageType.EVENT_TIMESTAMP_CHANGED:
            return 'Hey ' + Format.escape(first_name) + (', the following event was moved by more than 2 hours. I reset '
                                                         'your previous answer - please quickly fill out your attendance '
                                                         'for the moved event - thanks \n(Old event: ') \
                + Format.escape(extra_text) + ')'

        case MessageType.EVENT_ADDED:
            return 'Hey ' + Format.escape(first_name) + ', a new event was added - if you fill it out now, you don\'t have to think about it in the future...'
        case _:
            return message_type.name + ' ' + Format.escape(extra_text)


def generate_keyboard(all_commands: [str]) -> [[str]]:
    # The one static main-menu keyboard: a fixed layout, filtered to the commands the
    # user's role actually has. Buttons are Title-cased for display; Telegram echoes the
    # label back and Node.handle lowercases it, so the round-trip still matches.
    layout = [
        ['events'],
        ['admin'],
        ['website', 'help'],
    ]
    placed = {command for row in layout for command in row}

    result = [present for row in layout if (present := [c.title() for c in row if c in all_commands])]
    # Keep any command not covered by the fixed layout on its own row, so nothing silently disappears.
    result.extend([c] for c in all_commands if c not in placed)
    return result


class TelegramService(object):
    def __init__(self, bot: telegram.Bot, api_config: ApiConfig, user_state_service: UserStateService):
        self.bot = bot
        self.user_state_service = user_state_service
        self.maintainer_chat_id = api_config.get_key('Chat_Ids', 'MAINTAINER')
        self.trainers_games = api_config.get_int_list('Chat_Ids', 'TRAINERS_GAMES')
        self.trainers_training = api_config.get_int_list('Chat_Ids', 'TRAINERS_TRAINING')
        self.group_chat_id = api_config.get_key('Chat_Ids', 'GROUP_CHAT')

    async def _send_message(self, chat_id: int, message: str, reply_markup=None):
        try:
            return await self.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup,
                                               parse_mode=telegram.constants.ParseMode.HTML)
        except Forbidden as e:
            self.user_state_service.set_user_inactive(chat_id)
            await self.send_maintainer_message(
                f'Exception in _send_message: Forbidden\nUser: {chat_id}\nSetting User to Inactive\nMessage: {message}\nError: {e}')

    async def send_message(self, update: Update | TelegramUser, all_buttons: [str], message_type: MessageType = None,
                           message: str = None, message_extra_text: str = '', reply_markup=None):
        chat_id = update.effective_chat.id if type(update) is Update else update.telegramId
        first_name = update.effective_user.first_name if type(update) is Update else update.firstname
        if message is None:
            message = get_text(message_type, first_name=first_name, extra_text=message_extra_text)
        if reply_markup is None:
            reply_markup = self.get_reply_keyboard(message_type, all_buttons)
        messages_to_send = PrintUtils.split_message(message)
        if len(messages_to_send) > 1:
            await self.send_maintainer_message('Message too long (1): \n\n' + message)

        return await self._send_message(chat_id=chat_id, message=messages_to_send[0], reply_markup=reply_markup)

    async def send_file(self, update: Update | TelegramUser, path: str):
        chat_id = update.effective_chat.id if type(update) is Update else update.telegramId
        await self.bot.send_document(chat_id=chat_id, document=path)

    async def send_info_message_to_trainers(self, message: str, event_type: Event):
        messages_to_send = PrintUtils.split_message(message)
        if len(messages_to_send) > 1:
            await self.send_maintainer_message('Message too long (3): \n\n' + message)
        chat_ids = self.get_chat_ids(event_type)
        for chat_id in chat_ids:
            for message_to_send in messages_to_send:
                await self._send_message(chat_id=chat_id, message=message_to_send, reply_markup=None)

    @dispatch(str)
    async def send_maintainer_message(self, message: str):
        # Diagnostic content is arbitrary (may contain HTML-significant chars or our own
        # markup), so it is escaped wholesale into a monospace block.
        text = Format.bold('ℹ️ INFO') + '\n' + Format.pre(message)
        messages_to_send = PrintUtils.split_message(text)
        return await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=messages_to_send[0],
                                           parse_mode=telegram.constants.ParseMode.HTML)

    @dispatch(str, Exception)
    async def send_maintainer_message(self, description: str, error: Exception):
        error_message = repr(error) + '\n' + traceback.format_exc()
        text = Format.bold('⚠️ ERROR') + '\n' + Format.escape(description) + '\n' + Format.pre(error_message)
        messages_to_send = PrintUtils.split_message(text)
        for message_to_send in messages_to_send:
            await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                        parse_mode=telegram.constants.ParseMode.HTML)

    @dispatch(str, Update, Exception)
    async def send_maintainer_message(self, description: str, update: Update, error: Exception):
        error_message = repr(error) + '\n' + traceback.format_exc()
        text = Format.bold('⚠️ ERROR') + '\n' + Format.escape(description) + '\n' \
            + Format.pre(str(update) + '\n\n' + error_message)
        messages_to_send = PrintUtils.split_message(text)
        for message_to_send in messages_to_send:
            await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                        parse_mode=telegram.constants.ParseMode.HTML)

    async def report_exception(self, description: str, error: Exception, update: Update | None = None):
        """Report an unhandled exception: log it, then best-effort notify the maintainer. The log
        happens first and unconditionally, so a failure stays visible in the logs (greppable,
        alertable) even when the notification send itself fails.

        The maintainer is notified for every exception. Expected (control-flow) exceptions are
        logged at info and sent as a short notice without a stacktrace; genuinely unexpected
        ones are logged at error and sent with the full stacktrace (and Update, if present)."""
        expected = isinstance(error, ExpectedException)
        if expected:
            logging.info('%s (expected): %r', description, error)
        else:
            logging.error(description, exc_info=error)
        try:
            if expected:
                await self.send_maintainer_message(f'{description}: {error!r}')
            elif update is None:
                await self.send_maintainer_message(description, error)
            else:
                await self.send_maintainer_message(description, update, error)
        except Exception:
            logging.exception('Failed to send maintainer alert for: %s', description)

    async def send_maintainer_hi(self, hi: str):
        messages_to_send = PrintUtils.split_message(Format.escape(hi))
        for message_to_send in messages_to_send:
            await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                        parse_mode=telegram.constants.ParseMode.HTML)

    async def send_group_message(self, message: str):
        # Caller builds the HTML via the Format helpers (dynamic parts already escaped).
        return await self.bot.send_message(chat_id=int(self.group_chat_id), text=message,
                                           parse_mode=telegram.constants.ParseMode.HTML)

    def get_reply_keyboard(self, message_type: MessageType, all_commands: [str]):
        match message_type:
            case MessageType.WRONG_START_COMMAND:
                keyboard = [['/start']]
                return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            case MessageType.REJECTED:
                return None

        if all_commands is None or len(all_commands) == 0:
            return None
        return ReplyKeyboardMarkup(generate_keyboard(all_commands), one_time_keyboard=False)

    def get_chat_ids(self, event_type):
        match event_type:
            case Event.GAME:
                return self.trainers_games
            case Event.TRAINING:
                return self.trainers_training
            case Event.TIMEKEEPING:
                return self.trainers_games
        return []

    async def edit_inline_message_text(self, message: str, message_id: int, chat_id: int,
                                       reply_markup: InlineKeyboardMarkup = None):
        await self.bot.edit_message_text(text=message, message_id=message_id, chat_id=chat_id,
                                         reply_markup=reply_markup,
                                         parse_mode=telegram.constants.ParseMode.HTML)

    async def edit_callback_message(self, query, message: str, reply_markup: InlineKeyboardMarkup = None):
        await query.edit_message_text(text=message, reply_markup=reply_markup,
                                      parse_mode=telegram.constants.ParseMode.HTML)

    async def _delete_message(self, message_id: int, chat_id: int):
        try:
            await self.bot.delete_message(message_id=message_id, chat_id=chat_id)
        except BadRequest as e:
            # Bots can't delete messages older than 48h; this cleanup is best-effort.
            logging.debug(f"Could not delete message {message_id} in chat {chat_id}: {e}")
