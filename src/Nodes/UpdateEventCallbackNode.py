from telegram import Update

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


class UpdateEventCallbackNode(CallbackNode):
    def __init__(self, telegram_service: TelegramService, data_access: DataAccess, trigger_service: TriggerService,
                 node_handler):
        super().__init__(telegram_service, data_access, trigger_service)
        self.node_handler = node_handler

    async def handle(self, update: Update):
        query = update.callback_query
        _, event_type, callback_option, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        match event_type:
            case Event.GAME:
                event_summary = PrintUtils.pretty_print_long(self.data_access.get_game(doc_id))
                new_state = UserState.ADMIN_UPDATE_GAME
            case Event.TRAINING:
                event_summary = PrintUtils.pretty_print(self.data_access.get_training(doc_id))
                new_state = UserState.ADMIN_UPDATE_TRAINING
            case Event.TIMEKEEPING:
                event_summary = PrintUtils.pretty_print(self.data_access.get_timekeeping(doc_id))
                new_state = UserState.ADMIN_UPDATE_TIMEKEEPING

        event_type_string = event_type.name.lower().title()

        message = 'Not Implemented'
        reply_markup = None

        match callback_option:
            case CallbackOption.UPDATE:
                # send the 3 options
                await self.send_normal_message(update, 'Not implemented yet 😼️', new_state)
                await query.answer()
                return
            case CallbackOption.DELETE:
                # send yes/no
                message = 'Delete ' + event_type_string + '? (' + event_summary + ')'
                reply_markup = CallbackUtils.get_yes_or_no_markup(event_type, doc_id)
            case CallbackOption.NO:
                message = 'Update / Delete ' + event_type_string + ': ' + event_summary
                reply_markup = CallbackUtils.get_update_or_delete_reply_markup(event_type, doc_id)
            case CallbackOption.YES:
                message = 'Deleting ' + event_type_string + '...'
                await query.answer()
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                self.data_access.delete_event(event_type, doc_id)
                self.node_handler.recalculate_node_transitions()
                await self.send_normal_message(update, 'Deleted' + event_type_string + ' 👍', new_state)
                return

        await query.answer()
        await query.edit_message_text(text=message, reply_markup=reply_markup)

    async def send_normal_message(self, update: Update, message: str, new_state: UserState):
        node = self.node_handler.nodes[new_state]
        await self.telegram_service.send_message(
            update=update,
            all_buttons=node.get_commands_for_buttons(Role.ADMIN, new_state, update.effective_chat.id),
            message=message)
