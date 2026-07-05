"""Shared helpers for characterization tests: Update factories, user seeding, flow drivers."""
from datetime import datetime
from types import SimpleNamespace

from telegram import Update, Message, Chat, User, ChatMemberAdministrator
from telegram.constants import ChatType

from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from domain.entities.TelegramUser import TelegramUser
from domain.entities.Attendance import Attendance
from data.TenantContext import peek_team_id


# TelegramService branches on `type(update) is Update`, so tests must pass real
# telegram objects, not fakes.
def make_text_update(chat_id: int, text: str, first_name: str = "Test",
                     last_name: str = "User", update_id: int = 1) -> Update:
    chat = Chat(id=chat_id, type=ChatType.PRIVATE)
    user = User(id=chat_id, first_name=first_name, last_name=last_name, is_bot=False)
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text=text)
    return Update(update_id=update_id, message=message)


def make_group_update(group_chat_id: int, from_user_id: int, text: str, update_id: int = 1) -> Update:
    """A real telegram Update sent to a GROUP chat, from a user distinct from the chat.
    Mirrors make_text_update but flips the chat type so NodeHandler takes its group branch
    (where only /register_team is acted on)."""
    chat = Chat(id=group_chat_id, type=ChatType.GROUP)
    user = User(id=from_user_id, first_name="Group", last_name="Member", is_bot=False)
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=user, text=text)
    return Update(update_id=update_id, message=message)


async def drive_group(node_handler, group_chat_id: int, from_user_id: int, text: str) -> None:
    """Feed one group-chat text message through the real NodeHandler entry point."""
    await node_handler.handle_message(make_group_update(group_chat_id, from_user_id, text), context=None)


def make_my_chat_member_update(group_chat_id: int, title: str, user_id: int, first_name: str,
                               old_status: str, new_status: str):
    """The bot's own membership changed in a group. A REAL Update (like
    make_group_update): the error-report funnel dispatches on the Update type, so a
    SimpleNamespace here would silently disable assert_no_error_reported."""
    import datetime
    from telegram import ChatMemberUpdated, ChatMemberMember, ChatMemberLeft
    bot_user = User(id=999999, first_name='Bot', is_bot=True)
    members = {
        'member': ChatMemberMember(user=bot_user),
        'left': ChatMemberLeft(user=bot_user),
        'administrator': group_admin_member(999999),
    }
    return Update(
        update_id=1,
        my_chat_member=ChatMemberUpdated(
            chat=Chat(id=group_chat_id, type=ChatType.SUPERGROUP, title=title),
            from_user=User(id=user_id, first_name=first_name, is_bot=False),
            date=datetime.datetime.now(),
            old_chat_member=members[str(old_status)],
            new_chat_member=members[str(new_status)],
        ),
    )


def group_admin_member(user_id: int) -> ChatMemberAdministrator:
    """A real ChatMemberAdministrator (TeamRegistration checks `type(member) in (...)`, so
    a SimpleNamespace won't do). All the granular permission flags are irrelevant to the
    membership check, so they're all False."""
    return ChatMemberAdministrator(
        user=User(id=user_id, first_name="Admin", is_bot=False),
        can_be_edited=False, is_anonymous=False, can_manage_chat=False,
        can_delete_messages=False, can_manage_video_chats=False, can_restrict_members=False,
        can_promote_members=False, can_change_info=False, can_invite_users=False,
        can_post_stories=False, can_edit_stories=False, can_delete_stories=False)


def seed_user(data_access, telegram_id: int, role: Role, state: UserState,
              first_name: str = "Test", additional_info: str = "", team_id: str = None):
    """Create a user already past /start, in a known role + state. Returns the UsersToState.

    Stamps the ambient team by default so seeded users belong to the fixture's team;
    pass team_id explicitly to seed a teamless (INIT/REJECTED) or cross-team user."""
    user_to_state = data_access.add(TelegramUser(telegram_id, first_name, "User"))
    user_to_state.role = role
    user_to_state.state = state
    user_to_state.additional_info = additional_info
    user_to_state.team_id = team_id if team_id is not None else peek_team_id()
    data_access.update(user_to_state)
    return user_to_state


def set_attendance(data_access, user_id: str, event_doc_id: str, state: AttendanceState,
                   event_type: Event = Event.GAME) -> Attendance:
    return data_access.update_attendance(Attendance(user_id, event_doc_id, state), event_type)


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
        message=None, my_chat_member=None,
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
