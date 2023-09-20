from abc import ABC

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService


class CallbackNode(ABC):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.trigger_service = trigger_service
