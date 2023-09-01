from abc import ABC

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService

from Enums.UserState import UserState


class CallbackNode(ABC):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, user_states: [UserState]):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.user_states = user_states

    def can_handle(self, user_state: UserState):
        return user_state in self.user_states
