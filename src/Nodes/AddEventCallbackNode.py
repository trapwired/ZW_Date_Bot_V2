from telegram import Update, CallbackQuery

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils
from Utils import PrintUtils

from Enums.Event import Event
from Enums.CallbackOption import CallbackOption
from Enums.Role import Role
from Enums.UserState import UserState

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.UserStateService import UserStateService

from Utils import UpdateEventUtils


class AddEventCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 node_handler, user_state_service: UserStateService):
        super().__init__(telegram_service, data_access, trigger_service)
        self.node_handler = node_handler
        self.user_state_service = user_state_service

    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, callback_option, _ = CallbackUtils.try_parse_callback_message(query.data)

        match callback_option:
            case CallbackOption.CANCEL:
                # TODO
                # reset additional data in user
                # send back to main admin menu + send message
                # delete temp-build-event message?
            case CallbackOption.RESTART:
                # reset temp-build-event message
                # send first message of add-flow again (maybe even call method from AdminAddNode with event_type?
