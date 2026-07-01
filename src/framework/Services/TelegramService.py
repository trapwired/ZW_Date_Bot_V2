import logging
import traceback

import telegram
from multipledispatch import dispatch
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, ReplyKeyboardRemove, \
    Message

from Enums.MessageType import MessageType
from Enums.Event import Event

from Utils import PrintUtils
from Utils import Format
from Utils.ApiConfig import ApiConfig

from domain.entities.TelegramUser import TelegramUser
from telegram.error import BadRequest, Forbidden

from framework.Services.UserStateService import UserStateService


def get_text(message_type: MessageType, extra_text: str = '', first_name: str = ''):
    match message_type:
        case MessageType.ERROR:
            return 'Something went wrong - please try again, the maintainer has been notified :)'
        case MessageType.HELP:
            return 'Help is on its way (' + Format.escape(extra_text) + ')'
        case MessageType.WRONG_START_COMMAND:
            return 'Please start chatting with me by sending the command /start'
        case MessageType.WELCOME:
            return 'Hi ' + Format.escape(first_name) + ', welcome to the ' + Format.bold('Züri West manager') + ' 👋'
        case MessageType.CONTINUE_LATER:
            return 'Cheerio ' + Format.escape(first_name) + '! 👋'
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

        case MessageType.STATS_OVERVIEW:
            return 'Do you want to show stats for a game, training or timekeeping-event?'
        case MessageType.STATS_TO_GAMES:
            return 'Click on the game you want to see the stats for'
        case MessageType.STATS_TO_TRAININGS:
            return 'Click on the training you want to see the stats for'
        case MessageType.STATS_TO_TIMEKEEPINGS:
            return 'Click on the timekeeping-event you want to see the stats for'

        case MessageType.EDIT_OVERVIEW:
            return 'Do you want to edit your attendance for a game, training or timekeeping-event?'
        case MessageType.EDIT_TO_GAMES:
            return 'Click on the game you want to change your attendance-status'
        case MessageType.EDIT_TO_TRAININGS:
            return 'Click on the training you want to change your attendance-status'
        case MessageType.EDIT_TO_TIMEKEEPINGS:
            return 'Click on the timekeeping-event you want to change your attendance-status'

        case MessageType.ADMIN:
            return '<b>Admin center</b>\nHere you can add, update and delete upcoming events...'
        case MessageType.ADMIN_ADD:
            return 'What kind of event do you want to add?'
        case MessageType.ADMIN_UPDATE:
            return 'Which kind of event do you want to update (or delete)?'
        case MessageType.ADMIN_UPDATE_TO_GAME:
            return 'Click on the game you want to update or delete'
        case MessageType.ADMIN_UPDATE_TO_TRAINING:
            return 'Click on the training you want to update or delete'
        case MessageType.ADMIN_UPDATE_TO_TIMEKEEPING:
            return 'Click on the timekeeping-event you want to update or delete'

        case MessageType.TKE_ALREADY_FULL:
            return 'For the chosen timekeeping event already enough people have registered'

        case MessageType.ENROLLMENT_REMINDER:
            return 'Hey ' + Format.escape(first_name) + (', please quickly take your time to update your attendance '
                                                         'for the following upcoming event(s):')

        case MessageType.EVENT_TIMESTAMP_CHANGED:
            return 'Hey ' + Format.escape(first_name) + (', the following event was moved by more than 2 hours. I reset '
                                                         'your previous answer - please quickly fill out your attendance '
                                                         'for the moved event - thanks \n(Old event: ') \
                + Format.escape(extra_text) + ')'

        case MessageType.ADMIN_STATISTICS:
            return 'Here you are - which statistics do you like to see?'

        case MessageType.ADMIN_RESET_STATISTICS:
            return ('Are you sure you want to end the current season?\n\n'
                    'This permanently resets the reminder statistics for ALL players and cannot be undone.')

        case MessageType.EVENT_ADDED:
            return 'Hey ' + Format.escape(first_name) + ', a new event was added - if you fill it out now, you don\'t have to think about it in the future...'
        case _:
            return message_type.name + ' ' + Format.escape(extra_text)


def generate_keyboard(all_commands: [str]) -> [[str]]:
    first_cmds = ['overview', 'continue later']
    firsts = []
    events = []
    commands = []
    for cmd in all_commands:
        if cmd[0].isdigit():
            events.append(cmd)
        elif cmd in first_cmds:
            firsts.append(cmd)
        elif cmd != '/help':
            commands.append(cmd)

    result = [firsts]
    result.extend([e] for e in events)

    max_line_length = 15
    current_line_length = 0
    current_line = []
    for c in commands:
        if current_line_length + len(c) < max_line_length:
            current_line.append(c)
            current_line_length += len(c)
        else:
            result.append(current_line)
            current_line_length = len(c)
            current_line = [c]
    if len(current_line) > 0:
        result.append(current_line)
    result.append(['/help'])
    return result


def generate_admin_keyboard(all_commands: [str]) -> [[str]]:
    # Fixed layout for the admin overview; only rows whose commands the user actually has are shown.
    layout = [
        ['continue later'],
        ['/add', '/update'],
        ['/statistics'],
        ['/assign_roles', '/update_website'],
    ]
    placed = {command for row in layout for command in row} | {'/help'}

    result = [present for row in layout if (present := [c for c in row if c in all_commands])]
    # Keep any command not covered by the fixed layout on its own row, so nothing silently disappears.
    result.extend([c] for c in all_commands if c not in placed)
    result.append(['/help'])
    return result


def generate_statistics_keyboard(all_commands: [str]) -> [[str]]:
    # Fixed layout for the statistics screen; only rows whose commands the user actually has are shown.
    layout = [
        ['continue later'],
        ['/reminder_statistics', '/game_statistics'],
        ['/training_statistics', '/timekeeping_statistics'],
        ['/reset_statistics'],
    ]
    placed = {command for row in layout for command in row} | {'/help'}

    result = [present for row in layout if (present := [c for c in row if c in all_commands])]
    # Keep any command not covered by the fixed layout on its own row, so nothing silently disappears.
    result.extend([c] for c in all_commands if c not in placed)
    result.append(['/help'])
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

    async def send_message_with_normal_keyboard(self, update: Update | TelegramUser, message: str):
        chat_id = update.effective_chat.id if type(update) is Update else update.telegramId
        messages_to_send = PrintUtils.split_message(message)
        if len(messages_to_send) > 1:
            await self.send_maintainer_message('Message too long (2): \n\n' + message)
        # Return the sent message so callers (e.g. the add-event RESTART flow) can act on it,
        # matching send_message; without this it returned None and delete_previous_message crashed.
        return await self._send_message(chat_id=chat_id, message=messages_to_send[0],
                                        reply_markup=ReplyKeyboardRemove())

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
        """Report an unhandled exception: log it with a traceback, then best-effort alert the
        maintainer. The log happens first and unconditionally, so a failure stays visible in
        the logs (greppable, alertable) even when the alert send itself fails or the maintainer
        is not watching the chat."""
        logging.error(description, exc_info=error)
        try:
            if update is None:
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
        if message_type == MessageType.ADMIN_STATISTICS:
            keyboard = generate_statistics_keyboard(all_commands)
        elif message_type == MessageType.ADMIN:
            keyboard = generate_admin_keyboard(all_commands)
        else:
            keyboard = generate_keyboard(all_commands)
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

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

    async def delete_previous_message(self, message: Message | None):
        if message is None:
            return
        await self._delete_message(message.message_id - 1, message.chat_id)

    async def delete_message(self, update: Update):
        if update.message:
            message = update.message
        elif update.callback_query:
            message = update.callback_query.message
        else:
            return
        await self._delete_message(message.message_id, message.chat_id)

    async def _delete_message(self, message_id: int, chat_id: int):
        try:
            await self.bot.deleteMessage(message_id=message_id, chat_id=chat_id)
        except BadRequest as e:
            # Bots can't delete messages older than 48h; this cleanup is best-effort.
            logging.debug(f"Could not delete message {message_id} in chat {chat_id}: {e}")
