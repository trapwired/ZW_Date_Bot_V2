from telegram import Update

from Nodes.Node import Node

from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils

from Utils import CallbackUtils


class StatsNode(Node):

    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str,
                              event_type: Event):
        stats = self.data_access.get_stats_event(document_id, event_type)
        stats_with_names = self.data_access.get_names(stats)
        event_summary = update.message.text
        if event_type is Event.GAME:
            event_summary = PrintUtils.pretty_print_long(self.data_access.get_game(document_id))
        message = PrintUtils.pretty_print_event_summary(stats_with_names, event_summary, event_type)

        # Hacky, but doesn't duplicate code - correct would be own node
        reply_markup = CallbackUtils.get_stats_event_reply_markup(UserState.EDIT, event_type, document_id)

        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message=message,
            reply_markup=reply_markup)
