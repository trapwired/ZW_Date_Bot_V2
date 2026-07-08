from abc import ABC

from data.DataAccess import DataAccess

from Enums import Audience

from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService


class CallbackNode(ABC):
    # Who may trigger this callback node. NodeHandler enforces it before dispatch,
    # mirroring Transition.audience for the text channel — so a forwarded inline button
    # can't let an unauthorized user run an admin action. Subclasses tighten this.
    audience = Audience.EVERYONE

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.trigger_service = trigger_service
