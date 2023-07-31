import telegram

from src.Enums.MessageType import MessageType


class TelegramService(object):
    def __init__(self, bot: telegram.Bot):
        self.bot = bot

    async def send_message(self, telegram_id: int, message_type: MessageType, extra_text: str = ''):
        text = self.get_text(message_type, extra_text)
        reply_keyboard = self.get_reply_keyboard(message_type, extra_text)
        await self.bot.send_message(chat_id=telegram_id, text=text, reply_markup=reply_keyboard)

    def get_text(self, message_type: MessageType, extra_text: str):
        match message_type:
            case MessageType.HELP:
                return 'Help is on its way'
            case _:
                return 'Default'

    def get_reply_keyboard(self, message_type: MessageType, extra_text: str):
        match message_type:
            case MessageType.HELP:
                return None
            case _:
                return None
