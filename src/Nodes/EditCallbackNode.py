from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils
from Utils import PrintUtils

from Enums.Event import Event
from Enums.UserState import UserState

from databaseEntities.Attendance import Attendance

from Triggers.TriggerPayload import TriggerPayload


class EditCallbackNode(CallbackNode):
    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, attendance_state, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        telegram_user = self.data_access.get_user(update.effective_chat.id)
        new_attendance = Attendance(telegram_user.doc_id, doc_id, attendance_state)

        attendance = self.data_access.update_attendance(new_attendance, event_type)

        match event_type:
            case Event.GAME:
                event = self.data_access.get_game(doc_id)
            case Event.TRAINING:
                event = self.data_access.get_training(doc_id)
            case Event.TIMEKEEPING:
                event = self.data_access.get_timekeeping(doc_id)

        message = PrintUtils.pretty_print(event, attendance)
        reply_markup = CallbackUtils.get_edit_event_reply_markup(UserState.EDIT, event_type, doc_id)
        await query.answer()

        if message == query.message.text:
            return
        await query.edit_message_text(text=message, reply_markup=reply_markup)

        trigger_payload = TriggerPayload(new_attendance=new_attendance, doc_id=doc_id, event_type=event_type)
        await self.trigger_service.check_triggers(trigger_payload)
