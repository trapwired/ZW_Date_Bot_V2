"""Characterization: one-time spectator invite deep links.

An admin mints a t.me/<bot>?start=<token> link from the panel; the token lives on
the team doc and dies on first redemption. '/start <token>' joins the sender as
spectator from both teamless states (INIT and REJECTED) and never burns
password-throttle attempts.
"""
from telegram import ChatMemberLeft, User

from Enums.Role import Role
from Enums.UserState import UserState
from domain.entities.Team import Team
from features.adminpanel import AdminMenu
from framework.Services.TeamService import TeamService
from tests.helpers import drive, drive_callback, seed_user, current_state, assert_no_error_reported

ADMIN_ID = 2100
GUEST_ID = 2101
TEAM_B_GROUP = -200999333


def _mint_token(data_access, default_team) -> str:
    return TeamService(data_access).create_spectator_invite(default_team)


async def test_admin_mints_link_and_token_lands_on_team_doc(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.SPECTATOR_INVITE))

    text = update.callback_query.edits[-1].text
    assert 'https://t.me/TestBot?start=' in text
    token = text.split('?start=')[1].split()[0]
    assert token in TeamService(data_access).get_team(default_team.doc_id).invite_tokens
    assert_no_error_reported(bot)


async def test_fresh_user_redeems_invite_and_token_dies(node_handler, data_access, bot, default_team):
    bot.default_chat_member = ChatMemberLeft(user=User(id=1, first_name='x', is_bot=False))
    token = _mint_token(data_access, default_team)

    await drive(node_handler, GUEST_ID, f'/start {token}')

    guest = data_access.get_user_state(GUEST_ID)
    assert guest.role == Role.SPECTATOR and guest.team_id == default_team.doc_id
    assert current_state(data_access, GUEST_ID) == UserState.DEFAULT
    texts = bot.texts_to(GUEST_ID)
    assert 'welcome' in texts[0].lower() and default_team.name in texts[1]
    assert token not in TeamService(data_access).get_team(default_team.doc_id).invite_tokens
    assert_no_error_reported(bot)


async def test_second_use_of_the_same_token_is_rejected(node_handler, data_access, bot, default_team):
    bot.default_chat_member = ChatMemberLeft(user=User(id=1, first_name='x', is_bot=False))
    token = _mint_token(data_access, default_team)
    await drive(node_handler, GUEST_ID, f'/start {token}')

    await drive(node_handler, GUEST_ID + 1, f'/start {token}')

    second = data_access.get_user_state(GUEST_ID + 1)
    assert second.role == Role.REJECTED and not second.team_id
    assert_no_error_reported(bot)


async def test_rejected_user_redeems_invite_without_burning_throttle(node_handler, data_access, bot,
                                                                     default_team):
    seed_user(data_access, GUEST_ID, Role.REJECTED, UserState.REJECTED, team_id='')
    token = _mint_token(data_access, default_team)

    await drive(node_handler, GUEST_ID, f'/start {token}')

    guest = data_access.get_user_state(GUEST_ID)
    assert guest.role == Role.SPECTATOR and guest.team_id == default_team.doc_id
    assert_no_error_reported(bot)


async def test_invalid_token_from_rejected_state_records_no_password_attempt(node_handler, data_access, bot,
                                                                             default_team):
    seed_user(data_access, GUEST_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    await drive(node_handler, GUEST_ID, '/start not-a-real-token')

    guest = data_access.get_user_state(GUEST_ID)
    assert guest.role == Role.REJECTED
    assert guest.additional_info == ''                     # throttle record untouched
    assert_no_error_reported(bot)


async def test_token_identifies_its_own_team(node_handler, data_access, bot, default_team):
    bot.default_chat_member = ChatMemberLeft(user=User(id=1, first_name='x', is_bot=False))
    team_b = data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP))
    token_b = TeamService(data_access).create_spectator_invite(team_b)

    await drive(node_handler, GUEST_ID, f'/start {token_b}')

    guest = data_access.get_user_state(GUEST_ID)
    assert guest.team_id == team_b.doc_id and guest.role == Role.SPECTATOR
    assert_no_error_reported(bot)


async def test_healed_admin_testing_their_own_link_is_not_demoted(node_handler, data_access, bot, default_team):
    # State healed back to INIT but team + ADMIN role intact - tapping their own
    # invite link must not re-role them, and the token must survive.
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.INIT)
    token = _mint_token(data_access, default_team)

    await drive(node_handler, ADMIN_ID, f'/start {token}')

    admin = data_access.get_user_state(ADMIN_ID)
    assert admin.role == Role.ADMIN
    assert token in TeamService(data_access).get_team(default_team.doc_id).invite_tokens
    assert_no_error_reported(bot)


def test_minting_past_the_cap_retires_the_oldest_link(data_access, default_team):
    service = TeamService(data_access)
    tokens = [service.create_spectator_invite(default_team)
              for _ in range(service.MAX_OUTSTANDING_INVITES + 1)]

    outstanding = service.get_team(default_team.doc_id).invite_tokens
    assert len(outstanding) == service.MAX_OUTSTANDING_INVITES
    assert tokens[0] not in outstanding and tokens[-1] in outstanding
