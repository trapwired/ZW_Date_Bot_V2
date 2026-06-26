from abc import ABC

from Data.DataAccess import DataAccess

from Enums.RoleSet import RoleSet

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService


class CallbackNode(ABC):
    # Roles allowed to trigger this callback node. NodeHandler enforces it before dispatch,
    # mirroring Transition.allowed_roles for the text channel — so a forwarded inline button
    # can't let an unauthorized user run an admin action. Subclasses tighten this.
    required_roles = RoleSet.EVERYONE

    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService):
        self.data_access = data_access
        self.telegram_service = telegram_service
        self.trigger_service = trigger_service
