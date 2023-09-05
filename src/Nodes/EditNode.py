from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils
from Utils import CallbackUtils


class EditNode(Node):
    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState,
                              document_id: str, event_type: Event):
        match event_type:
            case Event.GAME:
                event = self.data_access.get_game(document_id)
            case Event.TRAINING:
                event = self.data_access.get_training(document_id)
            case Event.TIMEKEEPING:
                event = self.data_access.get_timekeeping(document_id)

        attendance = self.data_access.get_attendance(update.effective_user.id, document_id, event_type)
        message = PrintUtils.pretty_print(event, attendance)
        reply_markup = CallbackUtils.get_reply_markup(UserState.EDIT, event_type, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message,
            reply_markup=reply_markup)
