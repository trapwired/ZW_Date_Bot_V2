from telegram import Update

from framework.Nodes.Node import Node

from Enums.UserState import UserState
from Enums.Event import Event

from domain.entities.UsersToState import UsersToState

from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService
from data.DataAccess import DataAccess

from Utils import PrintUtils
from Utils import CallbackUtils
from Utils import UpdateEventUtils


class UpdateNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_service = event_service

    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str,
                              event_type: Event):
        event_summary = update.message.text
        if event_type is Event.GAME:
            event_summary = PrintUtils.pretty_print_long(self.event_service.get_event(Event.GAME, document_id))
        message = UpdateEventUtils.get_inline_message('Update / Delete', event_type, event_summary)

        reply_markup = CallbackUtils.get_update_or_delete_reply_markup(event_type, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message,
            reply_markup=reply_markup)
