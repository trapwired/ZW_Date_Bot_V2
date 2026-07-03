"""Characterization: the admin trainer-routing slice (AP#T / AP#TL / AP#TX).

Trainer lists were config-seeded until now, with Firestore hand-edits as the only
way to change them. The admin menu's Trainers section shows where each event
group's messages go and lets an admin toggle roster members (and remove stray
seeded ids) - changes persist immediately and routing picks them up without a
restart (TeamService cache invalidation).
"""
from Enums.Event import Event
from Enums.Role import Role
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from framework.Services.TeamService import TeamService
from tests.conftest import DEFAULT_TEAM_TRAINERS
from tests.helpers import drive_callback, seed_user, assert_no_error_reported

ADMIN_ID = 1500
PLAYER_ID = 1501


async def test_menu_shows_current_trainers_and_group_chat_fallback(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    default_team.trainers_training.clear()
    data_access.update(default_team)

    update = await drive_callback(node_handler, ADMIN_ID, AdminMenu.encode(AdminMenu.TRAINERS_MENU))

    text = update.callback_query.edits[-1].text
    assert str(DEFAULT_TEAM_TRAINERS[0]) in text            # seeded ids outside the roster stay visible
    assert 'no trainers set' in text                        # empty training list -> fallback is spelled out
    assert_no_error_reported(bot)


async def test_toggle_list_offers_roster_members_and_stray_trainer_ids(node_handler, data_access, bot):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT, first_name='Coach')
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT, first_name='Pia')

    update = await drive_callback(node_handler, ADMIN_ID,
                                  AdminMenu.encode(AdminMenu.TRAINERS_LIST, int(Event.GAME)))

    buttons = [b.text for row in update.callback_query.edits[-1].reply_markup.inline_keyboard for b in row]
    assert any('Coach' in b for b in buttons)
    assert any('Pia' in b for b in buttons)
    assert any(str(DEFAULT_TEAM_TRAINERS[0]) in b for b in buttons)
    assert_no_error_reported(bot)


async def test_toggle_persists_and_second_toggle_removes(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)

    await drive_callback(node_handler, ADMIN_ID,
                         AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME), ADMIN_ID))
    # Fresh TeamService reads straight from storage - proves persistence, not cache.
    assert ADMIN_ID in TeamService(data_access).get_team(default_team.doc_id).trainers_games

    await drive_callback(node_handler, ADMIN_ID,
                         AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME), ADMIN_ID))
    assert ADMIN_ID not in TeamService(data_access).get_team(default_team.doc_id).trainers_games
    assert_no_error_reported(bot)


async def test_routing_follows_toggles_without_restart(node_handler, services, data_access, bot, default_team):
    # Remove both seeded stray ids, make the admin the only game trainer - the very next
    # trainer message must go to them (same TeamService instance the router reads).
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    for stray in DEFAULT_TEAM_TRAINERS:
        await drive_callback(node_handler, ADMIN_ID,
                             AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME), stray))
    await drive_callback(node_handler, ADMIN_ID,
                         AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME), ADMIN_ID))

    await services["telegram_service"].send_info_message_to_trainers('who scores?', Event.GAME)

    assert bot.texts_to(ADMIN_ID) == ['who scores?']
    for stray in DEFAULT_TEAM_TRAINERS:
        assert bot.texts_to(stray) == []
    assert_no_error_reported(bot)


async def test_malformed_trainer_callbacks_are_ignored(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADMIN_ID, Role.ADMIN, UserState.DEFAULT)
    before = TeamService(data_access).get_team(default_team.doc_id).trainers_games

    for data in [AdminMenu.encode(AdminMenu.TRAINERS_LIST),                       # missing event arg
                 AdminMenu.encode(AdminMenu.TRAINERS_TOGGLE, int(Event.GAME))]:   # missing id arg
        await drive_callback(node_handler, ADMIN_ID, data)

    assert TeamService(data_access).get_team(default_team.doc_id).trainers_games == before
    assert_no_error_reported(bot)
