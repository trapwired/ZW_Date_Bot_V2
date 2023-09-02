from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils

from Enums.UserState import UserState

from databaseEntities.Attendance import Attendance


class EditCallbackNode(CallbackNode):
    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, attendance_state, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        telegram_user = self.data_access.get_user(update.effective_chat.id)
        new_attendance = Attendance(telegram_user.doc_id, doc_id, attendance_state)

        attendance = self.data_access.update_attendance(new_attendance, event_type)

        # TODO get event + prettyPrint

        # TODO adjust message (prettyPrint + newAttendanceState)

        # TODO send keyboard again

        await query.answer()
        await query.edit_message_text(text=f"{attendance}")
