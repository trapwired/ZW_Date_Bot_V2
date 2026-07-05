"""Characterization: the /start onboarding and rejected-user gate.

Pins current externally-observable behavior so later refactors can't change it
unnoticed.
"""
from telegram import ChatMemberLeft, ChatMemberMember, User

from Enums.Role import Role
from Enums.UserState import UserState
from domain.entities.Team import Team
from tests.helpers import drive, seed_user, current_state, assert_no_error_reported

NEW_USER_ID = 700
TEAM_B_GROUP = -100777
TEAM_B_PASSWORD = 'bergpass'


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
    bot.default_chat_member = ChatMemberLeft(user=User(id=1, first_name="x", is_bot=False))

    await drive(node_handler, NEW_USER_ID, "/start")

    assert current_state(data_access, NEW_USER_ID) == UserState.REJECTED
    assert data_access.get_user_state(NEW_USER_ID).role == Role.REJECTED
    assert any("two ways in" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_rejected_user_with_correct_password_reaches_default(node_handler, data_access, bot, api_config,
                                                                   default_team):
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    await drive(node_handler, NEW_USER_ID, api_config.get_key('Chats', 'SPECTATOR_PASSWORD'))

    updated = data_access.get_user_state(NEW_USER_ID)
    assert updated.state == UserState.DEFAULT
    assert updated.team_id == default_team.doc_id     # spectators get the team too
    assert_no_error_reported(bot)


# ---------------------------------------------------------------------------
# Multi-team: /start binds a user to whichever registered team's group they are
# in, and the WELCOME text carries that team's own name.
# ---------------------------------------------------------------------------

async def test_start_binds_member_of_a_second_teams_group(node_handler, data_access, bot):
    team_b = data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP))
    # Member of team B's group only: not the default team's group.
    bot.default_chat_member = ChatMemberLeft(user=User(id=1, first_name="x", is_bot=False))
    bot.chat_members[(TEAM_B_GROUP, NEW_USER_ID)] = ChatMemberMember(
        user=User(id=NEW_USER_ID, first_name="member", is_bot=False))

    await drive(node_handler, NEW_USER_ID, "/start")

    updated = data_access.get_user_state(NEW_USER_ID)
    assert updated.state == UserState.DEFAULT
    assert updated.role == Role.PLAYER
    assert updated.team_id == team_b.doc_id
    assert any("welcome to the" in m.text and "Berg" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_spectator_password_of_second_team_binds_to_that_team(node_handler, data_access, bot):
    team_b = data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP, spectator_password=TEAM_B_PASSWORD))
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    await drive(node_handler, NEW_USER_ID, TEAM_B_PASSWORD)

    updated = data_access.get_user_state(NEW_USER_ID)
    assert updated.state == UserState.DEFAULT
    assert updated.role == Role.SPECTATOR
    assert updated.team_id == team_b.doc_id
    assert any("welcome to the" in m.text and "Berg" in m.text for m in bot.sent)
    assert_no_error_reported(bot)


async def test_wrong_spectator_password_stays_rejected(node_handler, data_access, bot):
    data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP, spectator_password=TEAM_B_PASSWORD))
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    await drive(node_handler, NEW_USER_ID, "definitely-not-the-password")

    updated = data_access.get_user_state(NEW_USER_ID)
    assert updated.state == UserState.REJECTED
    assert updated.role == Role.REJECTED
    assert_no_error_reported(bot)


async def test_spectator_password_is_case_sensitive(node_handler, data_access, bot):
    # The password identifies the team; matching is exact and case-sensitive on raw text.
    data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP, spectator_password=TEAM_B_PASSWORD))
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    await drive(node_handler, NEW_USER_ID, TEAM_B_PASSWORD.upper())

    assert current_state(data_access, NEW_USER_ID) == UserState.REJECTED
    assert_no_error_reported(bot)


# ---------------------------------------------------------------------------
# Branding: the team name reaches the player-facing surfaces (WELCOME, website
# button label).
# ---------------------------------------------------------------------------

async def test_welcome_carries_the_teams_own_name(node_handler, data_access, bot, default_team):
    await drive(node_handler, NEW_USER_ID, "/start")

    assert any(default_team.name in m.text for m in bot.sent if "welcome to the" in m.text)
    assert_no_error_reported(bot)


async def test_website_button_is_labelled_with_the_team_name(node_handler, data_access, bot, default_team):
    data_access.set_website("https://club.example")
    seed_user(data_access, NEW_USER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, NEW_USER_ID, "website")

    labels = [b.text for m in bot.sent if m.reply_markup is not None
              for row in m.reply_markup.inline_keyboard for b in row]
    assert default_team.name in labels
    assert_no_error_reported(bot)


async def test_password_guessing_locks_after_max_attempts(node_handler, data_access, bot, api_config):
    from domain import SpectatorPasswordPolicy as policy
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    for attempt in range(policy.MAX_FAILED_ATTEMPTS):
        await drive(node_handler, NEW_USER_ID, f'wrong-guess-{attempt}')

    # Crossing the threshold alerted the maintainer exactly once.
    lockout_alerts = [m.text for m in bot.sent if 'lockout' in m.text]
    assert len(lockout_alerts) == 1

    # Even the CORRECT password is ignored while locked.
    await drive(node_handler, NEW_USER_ID, api_config.get_key('Chats', 'SPECTATOR_PASSWORD'))
    locked = data_access.get_user_state(NEW_USER_ID)
    assert locked.state == UserState.REJECTED
    assert locked.role == Role.REJECTED
    assert any('Too many attempts' in text for text in bot.texts_to(NEW_USER_ID))
    assert_no_error_reported(bot)


async def test_successful_password_clears_the_attempt_record(node_handler, data_access, bot, api_config,
                                                             default_team):
    seed_user(data_access, NEW_USER_ID, Role.REJECTED, UserState.REJECTED, team_id='')
    await drive(node_handler, NEW_USER_ID, 'wrong-guess')          # one failure on record

    await drive(node_handler, NEW_USER_ID, api_config.get_key('Chats', 'SPECTATOR_PASSWORD'))

    joined = data_access.get_user_state(NEW_USER_ID)
    assert joined.role == Role.SPECTATOR
    assert joined.team_id == default_team.doc_id
    assert joined.additional_info == ''                            # attempt record gone
    assert_no_error_reported(bot)
