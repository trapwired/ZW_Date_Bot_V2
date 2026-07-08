"""Characterization: the /register_team group command (multi-team onboarding).

A group's owner/admin (or the maintainer) claims that group as a team by sending
/register_team <name> in it. The group IS the team's identity anchor: one team per
group, and the issuer becomes the team's first admin. Everything else said in a group
stays ignored - NodeHandler only acts on this one command in its group branch.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from tests.helpers import drive_group, group_admin_member, seed_user, assert_no_error_reported

GROUP_B = -100999
ISSUER = 3100
OTHER_MEMBER = 3101


def _team_named(data_access, name):
    return next((t for t in data_access.get_all_teams() if t.name == name), None)


async def test_group_admin_registers_team_and_becomes_first_admin(node_handler, data_access, bot):
    bot.chat_members[(GROUP_B, ISSUER)] = group_admin_member(ISSUER)

    await drive_group(node_handler, GROUP_B, ISSUER, '/register_team Thunder')

    team = _team_named(data_access, 'Thunder')
    assert team is not None
    assert team.group_chat_id == GROUP_B

    issuer_state = data_access.get_user_state(ISSUER)
    assert issuer_state.role == Role.PLAYER and issuer_state.is_admin
    assert issuer_state.state == UserState.DEFAULT
    assert issuer_state.team_id == team.doc_id

    assert any('registered' in text for text in bot.texts_to(GROUP_B))
    assert_no_error_reported(bot)


async def test_register_team_parses_botname_suffix(node_handler, data_access, bot):
    # In groups Telegram may address commands explicitly: /register_team@SomeBot.
    bot.chat_members[(GROUP_B, ISSUER)] = group_admin_member(ISSUER)

    await drive_group(node_handler, GROUP_B, ISSUER, '/register_team@SomeBot Thunder')

    assert _team_named(data_access, 'Thunder') is not None
    assert_no_error_reported(bot)


async def test_non_admin_member_is_refused(node_handler, data_access, bot):
    # OTHER_MEMBER is not seeded into chat_members, so falls to the default member status.
    await drive_group(node_handler, GROUP_B, OTHER_MEMBER, '/register_team Thunder')

    assert _team_named(data_access, 'Thunder') is None
    assert any('admin' in text for text in bot.texts_to(GROUP_B))
    assert_no_error_reported(bot)


async def test_missing_team_name_shows_usage(node_handler, data_access, bot):
    bot.chat_members[(GROUP_B, ISSUER)] = group_admin_member(ISSUER)
    teams_before = len(data_access.get_all_teams())

    await drive_group(node_handler, GROUP_B, ISSUER, '/register_team')

    assert len(data_access.get_all_teams()) == teams_before
    assert any('/register_team followed by your team name' in text for text in bot.texts_to(GROUP_B))
    assert_no_error_reported(bot)


async def test_group_that_already_has_a_team_is_rejected(node_handler, data_access, bot, default_team):
    # Registering in the default team's own group chat: that group is already claimed.
    dup_issuer = 3200
    bot.chat_members[(default_team.group_chat_id, dup_issuer)] = group_admin_member(dup_issuer)
    teams_before = len(data_access.get_all_teams())

    await drive_group(node_handler, default_team.group_chat_id, dup_issuer, '/register_team Doppelganger')

    assert len(data_access.get_all_teams()) == teams_before
    assert any('already has a registered team' in text
               for text in bot.texts_to(default_team.group_chat_id))
    assert_no_error_reported(bot)


async def test_issuer_already_in_a_team_cannot_register_another(node_handler, data_access, bot, default_team):
    # One user, one team (ADR 0001): even a group admin already bound to a team is refused.
    seed_user(data_access, ISSUER, Role.PLAYER, UserState.DEFAULT, team_id=default_team.doc_id)
    bot.chat_members[(GROUP_B, ISSUER)] = group_admin_member(ISSUER)
    teams_before = len(data_access.get_all_teams())

    await drive_group(node_handler, GROUP_B, ISSUER, '/register_team Thunder')

    assert len(data_access.get_all_teams()) == teams_before
    assert _team_named(data_access, 'Thunder') is None
    assert any('already belong to a team' in text for text in bot.texts_to(GROUP_B))
    assert_no_error_reported(bot)


async def test_random_group_chatter_is_ignored(node_handler, data_access, bot):
    await drive_group(node_handler, GROUP_B, OTHER_MEMBER, 'hello')

    assert bot.sent == []
    assert_no_error_reported(bot)


async def test_whitespace_only_group_message_is_ignored(node_handler, data_access, bot):
    # str.split() on whitespace-only text yields no tokens - must not crash or reply.
    sent_before = len(bot.sent)

    await drive_group(node_handler, GROUP_B, ISSUER, '   ')

    assert len(bot.sent) == sent_before
    assert_no_error_reported(bot)
