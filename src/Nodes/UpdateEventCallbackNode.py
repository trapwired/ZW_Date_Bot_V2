from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils
from Utils import PrintUtils

from Enums.Event import Event
from Enums.UserState import UserState
from Enums.CallbackOption import CallbackOption

from databaseEntities.Attendance import Attendance

from Triggers.TriggerPayload import TriggerPayload


class UpdateEventCallbackNode(CallbackNode):
    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, callback_option, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        match event_type:
            case Event.GAME:
                event_summary = PrintUtils.pretty_print_long(self.data_access.get_game(doc_id))
            case Event.TRAINING:
                event_summary = PrintUtils.pretty_print(self.data_access.get_training(doc_id))
            case Event.TIMEKEEPING:
                event_summary = PrintUtils.pretty_print(self.data_access.get_timekeeping(doc_id))

        event_type_string = event_type.name.lower().title()

        message = 'Not Implemented'
        reply_markup = None

        match callback_option:
            case CallbackOption.UPDATE:
                # send the 3 options
                pass
            case CallbackOption.DELETE:
                # send yes/no
                message = 'Delete ' + event_type_string + '? (' + event_summary + ')'
                reply_markup = CallbackUtils.get_yes_or_no_markup(event_type, doc_id)
                pass
            case CallbackOption.NO:
                message = 'Update / Delete ' + event_type_string + ': ' + event_summary
                reply_markup = CallbackUtils.get_update_or_delete_reply_markup(event_type, doc_id)
            case CallbackOption.YES:
                message = 'Deleted ' + event_type_string + ' 👍'
                # TODO delete event via data_access

        await query.answer()
        await query.edit_message_text(text=message, reply_markup=reply_markup)
