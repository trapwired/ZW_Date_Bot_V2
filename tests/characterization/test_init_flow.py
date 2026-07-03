"""Characterization: the /start onboarding and rejected-user gate.

Pins current externally-observable behavior so later refactors can't change it
unnoticed.
"""
from telegram import ChatMemberLeft, User

from Enums.Role import Role
from Enums.UserState import UserState
from tests.helpers import drive, seed_user, current_state, assert_no_error_reported

NEW_USER_ID = 700


async def test_start_as_group_member_moves_to_default_and_welcomes(node_handler, data_access, default_team, bot):
    # Default FakeBot reports the user as a group member.
    await drive(node_handler, NEW_USER_ID, "/start")

    state = current_state(data_access, NEW_USER_ID)
    assert state == UserState.DEFAULT
    assert data_access.get_user_state(NEW_USER_ID).role == Role.PLAYER
    # /start binds the member to the team owning the configured group chat.
    assert data_access.get_user_state(NEW_USER_ID).team_id == default_team.doc_id
    assert any("welcome to the" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_start_as_non_member_is_rejected(node_handler, data_access, bot):
    bot.chat_member = ChatMemberLeft(user=User(id=1, first_name="x", is_bot=False))

    await drive(node_handler, NEW_USER_ID, "/start")

    assert current_state(data_access, NEW_USER_ID) == UserState.REJECTED
    assert data_access.get_user_state(NEW_USER_ID).role == Role.REJECTED
    assert any("not allowed" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_rejected_user_with_correct_password_reaches_default(node_handler, data_access, bot, api_config):
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED)

    await drive(node_handler, NEW_USER_ID, api_config.get_key('Chats', 'SPECTATOR_PASSWORD'))

    assert current_state(data_access, NEW_USER_ID) == UserState.DEFAULT
    assert_no_error_reported(bot)
