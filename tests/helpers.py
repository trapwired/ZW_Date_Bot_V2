"""Shared helpers for characterization tests: Update factory, user seeding, flow driver."""
from datetime import datetime

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
              first_name: str = "Test") -> None:
    """Create a user already past /start, in a known role + state."""
    user_to_state = data_access.add(TelegramUser(telegram_id, first_name, "User"))
    user_to_state.role = role
    user_to_state.state = state
    data_access.update(user_to_state)


async def drive(node_handler, chat_id: int, text: str) -> None:
    """Feed one text message through the real NodeHandler entry point."""
    await node_handler.handle_message(make_text_update(chat_id, text), context=None)


def current_state(data_access, telegram_id: int) -> UserState:
    return data_access.get_user_state(telegram_id).state


def assert_no_error_reported(bot) -> None:
    """Fail if the bot was asked to send a maintainer error report — catches silent failures."""
    errors = [m.text for m in bot.sent if "⚠️ ERROR" in m.text]
    assert not errors, f"NodeHandler reported error(s) to maintainer:\n{errors}"
