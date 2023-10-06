from Nodes.Node import Node
from telegram import Update

from Enums.UserState import UserState
from databaseEntities.UsersToState import UsersToState


class EditEventTimestampNode(Node):
    async def handle_event_timestamp(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # TODO add 2 new nodes for new states, and for each possibility one (2*3) each with parse (for string and datetime)

        # TryParse Input, format: 20.03.2023 19:38

        # if valid: , else send back: please retry, following format
        # load from UsersToState.additional_info: and split into doc_id and message_id

        # store in db - store response element for pretty print

        # Update inline_message with new string
        # build old string with new values

        # new user state?

        # send response: update ok

        # TODO inline message edit: self.telegram_service.edit_inline_message_text(text, inline_msg_id)

        await self.telegram_service.send_message(
            update=update,
            all_buttons=self.get_commands_for_buttons(user_to_state.role, new_state, update.effective_chat.id),
            message_type=MessageType.ADD)