import telegram
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup

from Enums.MessageType import MessageType

from Utils import PrintUtils


def get_text(message_type: MessageType, extra_text: str = '', first_name: str = ''):
    match message_type:
        case MessageType.ERROR:
            return 'An Exception was raised:    \n' + extra_text
        case MessageType.HELP:
            return 'Help is on its way (' + extra_text + ')'
        case MessageType.WRONG_START_COMMAND:
            return 'Please start chatting with me by sending the command /start'
        case MessageType.WELCOME:
            return 'Hi ' + first_name + ', welcome to the Züri west manager'
        case MessageType.CONTINUE_LATER:
            return 'Cheerio ' + first_name + '!'
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

        case _:
            return message_type.name + ' ' + extra_text


def get_reply_keyboard(message_type: MessageType, all_commands: [str]):
    match message_type:
        case MessageType.WRONG_START_COMMAND:
            keyboard = [['/start']]
            return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        case MessageType.REJECTED:
            return None
    keyboard = generate_keyboard(all_commands)
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)


def generate_keyboard(all_commands: [str]) -> [[str]]:
    all_commands.sort()
    result = []
    max_line_length = 25
    current_line_length = 0
    current_line = []
    for c in all_commands:
        if current_line_length + len(c) < max_line_length:
            current_line.append(c)
            current_line_length += len(c)
        else:
            result.append(current_line)
            current_line_length = len(c)
            current_line = [c]
    if len(current_line) > 0:
        result.append(current_line)
    return result


class TelegramService(object):
    def __init__(self, bot: telegram.Bot):
        self.bot = bot

    async def send_message(self, update: Update, all_buttons: [str], message_type: MessageType = None,
                           message: str = None, message_extra_text: str = '', reply_markup=None):
        chat_id = update.effective_chat.id
        first_name = update.effective_user.first_name
        if message is None:
            message = get_text(message_type, first_name=first_name, extra_text=message_extra_text)
        if reply_markup is None:
            reply_markup = get_reply_keyboard(message_type, all_buttons)
        message_to_send = PrintUtils.escape_message(message)
        await self.bot.send_message(chat_id=chat_id, text=message_to_send, reply_markup=reply_markup,
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)
