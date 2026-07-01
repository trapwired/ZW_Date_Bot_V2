from telegram import Update

from framework.Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState

from databaseEntities.UsersToState import UsersToState

from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService
from Data.DataAccess import DataAccess

from Utils import PrintUtils
from Utils import CallbackUtils


class EditNode(Node):
    def __init__(self, state: UserState, telegram_service: TelegramService, user_state_service: UserStateService,
                 data_access: DataAccess, event_service, attendance_service):
        super().__init__(state, telegram_service, user_state_service, data_access)
        self.event_service = event_service
        self.attendance_service = attendance_service

    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                              document_id: str, event_type: Event):
        event = self.event_service.get_event(event_type, document_id)
        yes_count = self.attendance_service.yes_count(document_id, event_type) if event_type is Event.TIMEKEEPING else 0

        attendance = self.attendance_service.get_attendance(update.effective_user.id, document_id, event_type)

        if attendance.state != AttendanceState.YES and \
                event_type == Event.TIMEKEEPING and \
                event.people_required <= yes_count:
            await self.telegram_service.send_message(
                update=update,
                all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
                message_type=MessageType.TKE_ALREADY_FULL
            )
            return

        message = PrintUtils.event_label(event_type) + ': ' + PrintUtils.pretty_print(event, attendance)
        reply_markup = CallbackUtils.get_edit_event_reply_markup(UserState.EDIT, event_type, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message,
            reply_markup=reply_markup)
