from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils

from Enums.UserState import UserState


class EditCallbackNode(CallbackNode):
    async def handle(self, update: Update):
        query = update.callback_query
        user_state, attendance_state, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        telegram_user = self.data_access.get_user(update.effective_chat.id)

        # TODO how to clever update game, training, tke with user
        # what if a entry does not exist? let repo handle

        # update game, training or tke
        match user_state:
            case UserState.EDIT_GAMES:
                pass
            case UserState.EDIT_TRAININGS:
                pass
            case UserState.EDIT_TIMEKEEPINGS:
                pass
        # adjust message

        # send keyboard again

        await query.answer()
        await query.edit_message_text(text=f"Selected option: {query.data}")
