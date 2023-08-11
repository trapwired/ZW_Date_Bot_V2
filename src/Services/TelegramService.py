import telegram
from telegram import ReplyKeyboardMarkup

from Enums.MessageType import MessageType


def get_text(message_type: MessageType, extra_text: str):
    match message_type:
        case MessageType.ERROR:
            return 'An Exception was raised:    \n' + extra_text
        case MessageType.HELP:
            return 'Help is on its way (' + extra_text + ')'  # TODO remove
        case MessageType.WRONG_START_COMMAND:
            return 'Please start chatting with me by sending the command /start'
        case MessageType.WELCOME:
            return 'Hi ' + extra_text + ', welcome to the Züri west manager'
        case MessageType.CONTINUE_LATER:
            return 'Cheerio ' + extra_text + '!'
        case _:
            return message_type.name + ' ' + extra_text


def get_reply_keyboard(message_type: MessageType, extra_text: str):
    keyboard = None
    match message_type:
        case MessageType.ERROR:
            keyboard = [['/help']]
        case MessageType.HELP:
            keyboard = [['starship Enterprise']]

    if keyboard is None:
        return keyboard
    return ReplyKeyboardMarkup(keyboard)


class TelegramService(object):
    def __init__(self, bot: telegram.Bot):
        self.bot = bot

    async def send_message(self, telegram_id: int, message_type: MessageType, extra_text: str = '', keyboard_btn_list=None):
        text = get_text(message_type, extra_text)
        if keyboard_btn_list is None:
            reply_keyboard = get_reply_keyboard(message_type, extra_text)
        else:
            reply_keyboard = ReplyKeyboardMarkup(keyboard_btn_list, one_time_keyboard=True)
        await self.bot.send_message(chat_id=telegram_id, text=text, reply_markup=reply_keyboard)
