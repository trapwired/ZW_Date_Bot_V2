import os

from telegram import Update, InputFile

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils
from Utils import PrintUtils

from Enums.CallbackOption import CallbackOption
from Enums.Event import Event
from Enums.UserState import UserState

from databaseEntities.Attendance import Attendance

from Data.DataAccess import DataAccess

from Services.TelegramService import TelegramService
from Services.TriggerService import TriggerService
from Services.IcsService import IcsService

from Triggers.TriggerPayload import TriggerPayload


class EditCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 ics_service: IcsService):
        super().__init__(telegram_service, data_access, trigger_service)
        self.ics_service = ics_service

    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, attendance_state, doc_id = CallbackUtils.try_parse_callback_message(query.data)
        telegram_user = self.data_access.get_user(update.effective_chat.id)

        match attendance_state:
            case CallbackOption.UNSURE:
                await self._write_database(telegram_user, query, event_type, attendance_state, doc_id)
            case CallbackOption.YES:
                await self._write_database(telegram_user, query, event_type, attendance_state, doc_id)
            case CallbackOption.NO:
                await self._write_database(telegram_user, query, event_type, attendance_state, doc_id)
            case CallbackOption.CALENDAR:
                await self._send_ics(query, update, event_type, doc_id)


    async def _write_database(self, telegram_user, query, event_type, attendance_state, doc_id):
        
        new_attendance = Attendance(telegram_user.doc_id, doc_id, attendance_state)

        attendance = self.data_access.update_attendance(new_attendance, event_type)

        match event_type:
            case Event.GAME:
                event = self.data_access.get_game(doc_id)
            case Event.TRAINING:
                event = self.data_access.get_training(doc_id)
            case Event.TIMEKEEPING:
                event = self.data_access.get_timekeeping(doc_id)

        message = event_type.name.lower().title() + ': ' + PrintUtils.pretty_print(event, attendance)
        reply_markup = CallbackUtils.get_edit_event_reply_markup(UserState.EDIT, event_type, doc_id)
        await query.answer()

        if message == query.message.text:
            return
        await query.edit_message_text(text=message, reply_markup=reply_markup)

        trigger_payload = TriggerPayload(new_attendance=new_attendance, doc_id=doc_id, event_type=event_type)
        await self.trigger_service.check_triggers(trigger_payload)
        return


    async def _send_ics(self, query, update, event_type, doc_id):
        await query.answer()

        ics_file_path = self.ics_service.get_ics(event_type, doc_id)

        with open(ics_file_path, "rb") as ics_file:
            await self.telegram_service.send_file(update, path=InputFile(ics_file))

        os.remove(ics_file_path)
        return
