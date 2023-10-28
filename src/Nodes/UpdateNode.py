from telegram import Update

from Nodes.Node import Node

from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils
from Utils import CallbackUtils
from Utils import UpdateEventUtils


class UpdateNode(Node):
    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str,
                              event_type: Event):
        event_summary = update.message.text
        if event_type is Event.GAME:
            event_summary = PrintUtils.pretty_print_long(self.data_access.get_game(document_id))
        message = UpdateEventUtils.get_inline_message('Update / Delete', event_type, event_summary)

        reply_markup = CallbackUtils.get_update_or_delete_reply_markup(event_type, document_id)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message,
            reply_markup=reply_markup)
