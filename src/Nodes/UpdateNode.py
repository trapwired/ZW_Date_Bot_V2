from telegram import Update

from Nodes.Node import Node

from Enums.UserState import UserState
from Enums.Event import Event

from databaseEntities.UsersToState import UsersToState

from Utils import PrintUtils


class UpdateNode(Node):
    async def handle_event_id(self, update: Update, user_to_state: UsersToState, new_state: UserState, document_id: str,
                              event_type: Event):
        event_summary = update.message.text
        if event_type is Event.GAME:
            event_summary = PrintUtils.pretty_print_long(self.data_access.get_game(document_id))
        message = 'Update or add ' + event_summary
        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state),
            message=message)
