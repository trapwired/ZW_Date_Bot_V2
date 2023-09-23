from telegram import Update

from Nodes.Node import Node

from Enums.MessageType import MessageType
from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils


class StatsNode(Node):

    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str,
                              event_type: Event):
        stats = self.data_access.get_stats_event(document_id, event_type)
        stats_with_names = self.data_access.get_names(stats)
        message = PrintUtils.pretty_print_event_summary(stats_with_names, update.message.text, event_type)
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message)
