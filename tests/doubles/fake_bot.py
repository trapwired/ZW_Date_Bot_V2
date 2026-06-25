"""Recording stand-in for telegram.Bot.

Doubled at the Bot boundary so the real TelegramService (formatting, keyboard
generation, message splitting) runs under test. Every outbound call is recorded
so tests can assert on what the bot was told to send.
"""
from types import SimpleNamespace

from telegram import ChatMemberMember, User


class FakeBot:
    def __init__(self):
        self.sent = []          # send_message calls
        self.edits = []         # edit_message_text calls
        self.documents = []     # send_document calls
        self.deleted = []       # deleteMessage calls
        self._message_id = 0
        # Default: every queried user is a group member. Tests override to exercise rejection.
        self.chat_member = ChatMemberMember(user=User(id=1, first_name="member", is_bot=False))

    def _next_message_id(self) -> int:
        self._message_id += 1
        return self._message_id

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        message_id = self._next_message_id()
        # Mirror the telegram.Message surface callers read off the return value:
        # .message_id, .id and .chat.id (see AdminAddNode).
        record = SimpleNamespace(
            chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode,
            message_id=message_id, id=message_id, chat=SimpleNamespace(id=chat_id),
        )
        self.sent.append(record)
        return record

    async def get_chat_member(self, chat_id, user_id):
        return self.chat_member

    async def send_document(self, chat_id, document):
        self.documents.append(SimpleNamespace(chat_id=chat_id, document=document))

    async def edit_message_text(self, text, message_id, chat_id, reply_markup=None, parse_mode=None):
        self.edits.append(SimpleNamespace(
            text=text, message_id=message_id, chat_id=chat_id, reply_markup=reply_markup))

    async def deleteMessage(self, message_id, chat_id):  # noqa: N802 - matches telegram.Bot
        self.deleted.append(SimpleNamespace(message_id=message_id, chat_id=chat_id))

    def texts_to(self, chat_id):
        """All message texts sent to a given chat, in order — convenience for assertions."""
        return [m.text for m in self.sent if m.chat_id == chat_id]
