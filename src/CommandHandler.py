from telegram import Update
from telegram.ext import ContextTypes, BaseHandler
from telegram.ext._utils.types import CCT


class CommandHandler(BaseHandler[Update, CCT]):

    __slots__ = ("commands", "filters")

    # list of all workflows
    # playerStateService
    # AdminService

    def __init__(self):
        super().__init__(self.handle_message)

    def check_update(self, update: object):
        if isinstance(update, Update):
            return True
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.text:
            return
        await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

        # def handle(self): # signature?
        # get player state
        # get applicable workflow (state, command)
        # workflow.handle

