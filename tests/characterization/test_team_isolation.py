"""Characterization: end-to-end tenant isolation between two teams.

The flagship multi-tenancy test. Two teams are built the way real onboarding builds
them - team A via the fixture + a seeded admin, team B via the real /register_team group
command - and then driven THROUGH NodeHandler. Everything team-scoped (events, roster)
must stay partitioned: one team's admin never sees the other's game or players.
"""
from Enums.Role import Role
from Enums.UserState import UserState
from Enums.Event import Event
from data.TenantContext import team_context
from features.adminpanel import AdminMenu
from tests.helpers import (drive, drive_callback, drive_group, seed_user, group_admin_member,
                           assert_no_error_reported)

TEAM_A_ADMIN = 4100
GROUP_B = -100555
TEAM_B_ADMIN = 4200          # becomes team B's first admin by registering it
FUTURE_TIMESTAMP = "24.12.2030 18:30"


def _start(event_type: Event) -> str:
    return AdminMenu.encode(AdminMenu.ADD_CHOOSER, int(event_type))


async def test_two_teams_are_isolated_end_to_end(node_handler, data_access, bot, default_team):
    team_a = default_team
    seed_user(data_access, TEAM_A_ADMIN, Role.PLAYER, UserState.DEFAULT, is_admin=True)     # team A's admin

    # Team B is created for real: its group admin claims the group as a team and becomes
    # its first admin.
    bot.chat_members[(GROUP_B, TEAM_B_ADMIN)] = group_admin_member(TEAM_B_ADMIN)
    await drive_group(node_handler, GROUP_B, TEAM_B_ADMIN, '/register_team Berg')
    team_b = next(t for t in data_access.get_all_teams() if t.name == 'Berg')

    # Team A admin adds a game through the real admin-menu wizard.
    await drive_callback(node_handler, TEAM_A_ADMIN, _start(Event.GAME))
    await drive(node_handler, TEAM_A_ADMIN, FUTURE_TIMESTAMP)
    await drive(node_handler, TEAM_A_ADMIN, "Home Arena")
    await drive(node_handler, TEAM_A_ADMIN, "Rivals FC")
    await drive(node_handler, TEAM_A_ADMIN, "save")

    # Team B admin opens events - their own team has none.
    await drive(node_handler, TEAM_B_ADMIN, "events")
    assert any("no upcoming events" in text for text in bot.texts_to(TEAM_B_ADMIN))

    # Rosters and events stay partitioned per team.
    with team_context(team_a.doc_id):
        assert [p.telegramId for p in data_access.get_all_players()] == [TEAM_A_ADMIN]
        assert len(data_access.get_ordered_games()) == 1          # team A still sees its game

    with team_context(team_b.doc_id):
        assert [p.telegramId for p in data_access.get_all_players()] == [TEAM_B_ADMIN]
        assert data_access.get_ordered_games() == []              # team B has no games

    assert_no_error_reported(bot)
