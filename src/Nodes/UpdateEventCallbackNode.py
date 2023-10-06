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

from src.Utils import UpdateEventUtils


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

        if callback_option in [CallbackOption.UPDATE, CallbackOption.DELETE, CallbackOption.NO, CallbackOption.Back]:
            await self._handle_pure_callback(query, event_type_string, event_summary, event_type, doc_id,
                                             callback_option)
        else:
            await self._handle_callback_with_messages(update, event_type_string, event_summary, event_type, doc_id,
                                                      callback_option, new_state)

    async def _handle_pure_callback(self, query: CallbackQuery, event_type_string: str, event_summary: str,
                                    event_type: Event, doc_id: str, callback_option: CallbackOption):
        message = 'Not Implemented'
        reply_markup = None

        match callback_option:
            case CallbackOption.UPDATE:
                message = 'Update ' + event_type_string + ' (' + event_summary + ')'
                reply_markup = CallbackUtils.get_update_event_options(event_type, doc_id)
            case CallbackOption.DELETE:
                message = 'Delete ' + event_type_string + '? (' + event_summary + ')'
                reply_markup = CallbackUtils.get_yes_or_no_markup(event_type, doc_id)
            case CallbackOption.NO:
                message = 'Update / Delete ' + event_type_string + ': ' + event_summary
                reply_markup = CallbackUtils.get_update_or_delete_reply_markup(event_type, doc_id)
            case CallbackOption.Back:
                message = 'Update / Delete ' + event_type_string + ': ' + event_summary
                reply_markup = CallbackUtils.get_update_or_delete_reply_markup(event_type, doc_id)

        await query.answer()
        await query.edit_message_text(text=message, reply_markup=reply_markup)

    async def _handle_callback_with_messages(self, update: Update, event_type_string: str, event_summary: str,
                                             event_type: Event, doc_id: str, callback_option: CallbackOption,
                                             new_state: UserState):
        query = update.callback_query
        message = 'Not Implemented'
        reply_markup = None
        match callback_option:
            case CallbackOption.YES:
                message = 'Deleting ' + event_type_string + '...'
                await query.answer()
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                self.data_access.delete_event(event_type, doc_id)
                self.node_handler.recalculate_node_transitions()
                await self.send_normal_message(update, 'Deleted' + event_type_string + ' 👍', new_state)
                return

        if callback_option in [CallbackOption.DATETIME, CallbackOption.LOCATION, CallbackOption.OPPONENT]:
            updated_event_summary = UpdateEventUtils.mark_updating_in_event_string(event_type, event_summary,
                                                                                   callback_option)
            message = 'Updating ' + event_type_string + ': ' + updated_event_summary
            reply_markup = CallbackUtils.get_update_event_options(event_type, doc_id)
            await query.answer()
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            await self.send_normal_message_keyboard(update, 'Send me the new ' + callback_option.name.title())
            # TODO change user State, store callback_query in db? or via telegram?
            # TODO new callback handler, only for back if user in edit state, to send button-keyboard again
            return

        await query.answer()
        await query.edit_message_text(text=message, reply_markup=reply_markup)

    async def send_normal_message(self, update: Update, message: str, new_state: UserState):
        node = self.node_handler.nodes[new_state]
        await self.telegram_service.send_message(
            update=update,
            all_buttons=node.get_commands_for_buttons(Role.ADMIN, new_state, update.effective_chat.id),
            message=message)

    async def send_normal_message_keyboard(self, update: Update, message: str):
        await self.telegram_service.send_message_with_normal_keyboard(
            update=update,
            message=message)
