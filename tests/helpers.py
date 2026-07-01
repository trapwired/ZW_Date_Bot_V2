"""Shared helpers for characterization tests: Update factories, user seeding, flow drivers."""
from datetime import datetime
from types import SimpleNamespace

from telegram import Update, Message, Chat, User
from telegram.constants import ChatType

from Enums.Role import Role
from Enums.UserState import UserState
from databaseEntities.TelegramUser import TelegramUser


# TelegramService branches on `type(update) is Update`, so tests must pass real
# telegram objects, not fakes.
def make_text_update(chat_id: int, text: str, first_name: str = "Test",
                     last_name: str = "User", update_id: int = 1) -> Update:
    chat = Chat(id=chat_id, type=ChatType.PRIVATE)
    user = User(id=chat_id, first_name=first_name, last_name=last_name, is_bot=False)
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text=text)
    return Update(update_id=update_id, message=message)


def seed_user(data_access, telegram_id: int, role: Role, state: UserState,
              first_name: str = "Test", additional_info: str = ""):
    """Create a user already past /start, in a known role + state. Returns the UsersToState."""
    user_to_state = data_access.add(TelegramUser(telegram_id, first_name, "User"))
    user_to_state.role = role
    user_to_state.state = state
    user_to_state.additional_info = additional_info
    data_access.update(user_to_state)
    return user_to_state


async def drive(node_handler, chat_id: int, text: str) -> None:
    """Feed one text message through the real NodeHandler entry point."""
    await node_handler.handle_message(make_text_update(chat_id, text), context=None)


class FakeCallbackQuery:
    """Records answer()/edit_message_text() instead of hitting Telegram."""

    def __init__(self, data: str, chat_id: int, message_text: str, message_id: int):
        self.data = data
        self.id = "cbq1"
        self.from_user = SimpleNamespace(id=chat_id, first_name="Test")
        self.answered = False
        self.edits = []
        self.message = SimpleNamespace(text_html=message_text, chat=SimpleNamespace(id=chat_id),
                                       chat_id=chat_id, message_id=message_id, id=message_id)

    async def answer(self, *args, **kwargs):
        self.answered = True

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.edits.append(SimpleNamespace(text=text, reply_markup=reply_markup))


def make_callback_update(chat_id: int, data: str, message_text: str = "", message_id: int = 10,
                         first_name: str = "Test"):
    """A callback-query Update. Not a real telegram.Update: TelegramService falls to its
    TelegramUser branch (telegramId/firstname) for non-Update inputs, which is what we want."""
    return SimpleNamespace(
        effective_chat=SimpleNamespace(id=chat_id, type=ChatType.PRIVATE),
        effective_user=SimpleNamespace(id=chat_id, first_name=first_name, last_name="User"),
        message=None,
        callback_query=FakeCallbackQuery(data, chat_id, message_text, message_id),
        telegramId=chat_id,
        firstname=first_name,
    )


async def drive_callback(node_handler, chat_id: int, data: str, message_text: str = "",
                         message_id: int = 10):
    """Feed one callback-query through the real NodeHandler entry point; returns the update
    so tests can inspect the recorded query (answered / edits)."""
    update = make_callback_update(chat_id, data, message_text, message_id)
    await node_handler.handle_message(update, context=None)
    return update


def current_state(data_access, telegram_id: int) -> UserState:
    return data_access.get_user_state(telegram_id).state


def current_step(data_access, telegram_id: int):
    """The add-event wizard step held in the user's draft (TempData.step)."""
    user_id = data_access.get_user_state(telegram_id).user_id
    return data_access.get_temp_data(user_id).step


def assert_no_error_reported(bot) -> None:
    """Fail if the bot was asked to send a maintainer error report — catches silent failures."""
    errors = [m.text for m in bot.sent if "⚠️ ERROR" in m.text]
    assert not errors, f"NodeHandler reported error(s) to maintainer:\n{errors}"
