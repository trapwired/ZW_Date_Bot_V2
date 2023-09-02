from abc import ABC

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService


class CallbackNode(ABC):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess):
        self.data_access = data_access
        self.telegram_service = telegram_service
