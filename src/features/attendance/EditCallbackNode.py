import os

from telegram import Update, InputFile

from framework.Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils
from Utils import PrintUtils

from Enums.CallbackOption import CallbackOption
from Enums.UserState import UserState

from Data.DataAccess import DataAccess

from framework.Services.TelegramService import TelegramService
from framework.Services.TriggerService import TriggerService
from features.attendance.IcsService import IcsService

from Triggers.TriggerPayload import TriggerPayload


class EditCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 ics_service: IcsService, attendance_service):
        super().__init__(telegram_service, data_access, trigger_service)
        self.ics_service = ics_service
        self.attendance_service = attendance_service

    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, attendance_state, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        match attendance_state:
            case CallbackOption.UNSURE | CallbackOption.YES | CallbackOption.NO:
                await self._write_database(update, query, event_type, attendance_state, doc_id)
            case CallbackOption.CALENDAR:
                await self._send_ics(query, update, event_type, doc_id)

    async def _write_database(self, update, query, event_type, attendance_state, doc_id):
        attendance, event = self.attendance_service.set_attendance(
            update.effective_chat.id, event_type, doc_id, attendance_state)

        message = PrintUtils.event_label(event_type) + ': ' + PrintUtils.pretty_print(event, attendance)
        reply_markup = CallbackUtils.get_edit_event_reply_markup(UserState.EDIT, event_type, doc_id)
        await query.answer()

        if message == query.message.text_html:
            return
        await self.telegram_service.edit_callback_message(query, message, reply_markup)

        trigger_payload = TriggerPayload(new_attendance=attendance, doc_id=doc_id, event_type=event_type)
        await self.trigger_service.check_triggers(trigger_payload)
        return

    async def _send_ics(self, query, update, event_type, doc_id):
        ics_file_path = self.ics_service.get_ics(event_type, doc_id)

        with open(ics_file_path, "rb") as ics_file:
            await self.telegram_service.send_file(update, path=InputFile(ics_file))

        await query.answer()

        os.remove(ics_file_path)
        return
