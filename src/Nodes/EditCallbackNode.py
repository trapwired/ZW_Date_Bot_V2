from telegram import Update

from Nodes.CallbackNode import CallbackNode

from Utils import CallbackUtils


class EditCallbackNode(CallbackNode):
    async def handle(self, update: Update):
        query = update.callback_query
        user_state, attendance_state, doc_id = CallbackUtils.try_parse_callback_message(query.data)

        await query.answer()
        await query.edit_message_text(text=f"Selected option: {query.data}")
        # + send again keyboard? or only once?
