import telegram
from telegram import ReplyKeyboardMarkup

from Enums.MessageType import MessageType


def get_text(message_type: MessageType, extra_text: str):
    match message_type:
        case MessageType.ERROR:
            return 'Command not recognized. Please try again or type /help.'
        case MessageType.HELP:
            return 'Help is on its way'
        case MessageType.WRONG_START_COMMAND:
            return 'Please start chatting with me by sending the command /start'
        case MessageType.WELCOME:
            return 'Hi ' + extra_text + ', welcome to the Züri west manager'
        case _:
            return 'Default'


def get_reply_keyboard(message_type: MessageType, extra_text: str):
    keyboard = None
    match message_type:
        case MessageType.ERROR:
            keyboard = [['/help']]
        case MessageType.HELP:
            keyboard = ['starship Enterprise']

    if keyboard is None:
        return keyboard
    return ReplyKeyboardMarkup(keyboard)


class TelegramService(object):
    def __init__(self, bot: telegram.Bot):
        self.bot = bot

    async def send_message(self, telegram_id: int, message_type: MessageType, extra_text: str = ''):
        text = get_text(message_type, extra_text)
        reply_keyboard = get_reply_keyboard(message_type, extra_text)
        await self.bot.send_message(chat_id=telegram_id, text=text, reply_markup=reply_keyboard)
