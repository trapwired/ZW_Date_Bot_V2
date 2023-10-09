from Nodes.Node import Node
from telegram import Update

from Enums.UserState import UserState
from databaseEntities.UsersToState import UsersToState

from Utils import UpdateEventUtils
from Utils import CallbackUtils


class EditEventTimestampNode(Node):
    async def handle_event_timestamp(self, update: Update, user_to_state: UsersToState, new_state: UserState):
        # TODO add cancel logic
        # TODO tidy up additional data (or maybe dont?)
        # TODO add 2 new nodes for new states, and for each possibility one (2*3) each with parse (for string and datetime)
        # TODO add transitions from everywhere?
        # Add transition, new type, + cancel + evtl order of transitions?

        message = update.message.text.lower()
        # TODO handle cancel?
        parsed_string = UpdateEventUtils.parse_datetime_string(message)
        if type(parsed_string) is str:
            # Error case, send message without changing anything
            await self.telegram_service.send_message_with_normal_keyboard(
                update=update,
                message=parsed_string)
            return

        new_datetime = parsed_string

        # load from UsersToState.additional_info: and split into doc_id and message_id
        user_to_state = self.user_state_service.get_user_state(update.effective_chat.id)
        try_parse = CallbackUtils.try_parse_additional_information(user_to_state.additional_info)
        # additional_info = CallbackUtils.try_parse_additional_information(update.message)

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