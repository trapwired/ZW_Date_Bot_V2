"""Characterization: guided new-team onboarding (my_chat_member trigger).

Adding the bot to a group by a group admin registers that group as a team (name =
group title, adder = first admin) and DMs the adder the setup guide; removing the
bot from a still-fresh team rolls the whole setup back. Teamless private users get
an explicit two-way choice instead of a dead-end rejection.
"""
from telegram import ChatMemberLeft, User
from telegram.constants import ChatMemberStatus
from telegram.error import Forbidden

from Enums.Role import Role
from Enums.UserState import UserState
from features.adminpanel import AdminMenu
from features.onboarding import OnboardingMenu
from framework.Services.TeamService import TeamService
from tests.helpers import (drive, drive_callback, seed_user, current_state, assert_no_error_reported,
                           make_my_chat_member_update, group_admin_member)

GROUP = -200777001
ADDER_ID = 1900


def _added_update(chat_id=GROUP, title='SG Fluffy', user_id=ADDER_ID):
    return make_my_chat_member_update(chat_id, title, user_id, 'Dana',
                                      ChatMemberStatus.LEFT, ChatMemberStatus.MEMBER)


def _removed_update(chat_id=GROUP, title='SG Fluffy', user_id=ADDER_ID):
    return make_my_chat_member_update(chat_id, title, user_id, 'Dana',
                                      ChatMemberStatus.MEMBER, ChatMemberStatus.LEFT)


def _make_adder_group_admin(bot, chat_id=GROUP, user_id=ADDER_ID):
    bot.chat_members[(chat_id, user_id)] = group_admin_member(user_id)


async def test_added_by_group_admin_registers_team_and_dms_setup_guide(node_handler, data_access, bot):
    _make_adder_group_admin(bot)

    await node_handler.handle_message(_added_update(), context=None)

    team = TeamService(data_access).find_team_by_group_chat(GROUP)
    assert team is not None and team.name == 'SG Fluffy'
    adder_state = data_access.get_user_state(ADDER_ID)
    assert adder_state.role == Role.PLAYER and adder_state.is_admin and adder_state.team_id == team.doc_id
    dm = bot.texts_to(ADDER_ID)
    assert len(dm) == 1 and 'SG Fluffy' in dm[0] and 'Spectators' in dm[0]
    group_texts = bot.texts_to(GROUP)
    assert len(group_texts) == 1 and '/start to join' in group_texts[0]
    assert_no_error_reported(bot)


async def test_added_by_non_admin_registers_nothing_and_names_both_paths(node_handler, data_access, bot):
    # FakeBot's default chat member is a plain member - not enough to claim the group.
    await node_handler.handle_message(_added_update(), context=None)

    assert TeamService(data_access).find_team_by_group_chat(GROUP) is None
    group_texts = bot.texts_to(GROUP)
    assert len(group_texts) == 1
    assert 'group admin' in group_texts[0] and '/register_team' in group_texts[0]
    assert_no_error_reported(bot)


async def test_unreachable_adder_gets_group_fallback_with_start_link(node_handler, data_access, bot):
    _make_adder_group_admin(bot)
    original = bot.send_message

    async def send(chat_id, text, reply_markup=None, parse_mode=None):
        if chat_id == ADDER_ID:
            raise Forbidden('bot cannot initiate')
        return await original(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    bot.send_message = send

    await node_handler.handle_message(_added_update(), context=None)

    assert TeamService(data_access).find_team_by_group_chat(GROUP) is not None   # registration survives
    group_texts = bot.texts_to(GROUP)
    assert len(group_texts) == 1 and 't.me/TestBot' in group_texts[0]
    assert_no_error_reported(bot)


async def test_added_to_already_registered_group_registers_no_second_team(node_handler, data_access, bot,
                                                                          default_team):
    _make_adder_group_admin(bot, chat_id=default_team.group_chat_id)

    await node_handler.handle_message(
        _added_update(chat_id=default_team.group_chat_id, title='Whatever'), context=None)

    teams = TeamService(data_access).get_all_teams()
    assert len(teams) == 1
    group_texts = bot.texts_to(default_team.group_chat_id)
    assert len(group_texts) == 1 and default_team.name in group_texts[0]
    assert_no_error_reported(bot)


async def test_removal_from_fresh_team_rolls_the_setup_back(node_handler, data_access, bot, api_config):
    from data.TenantContext import team_context
    from Enums.Table import Table
    _make_adder_group_admin(bot)
    await node_handler.handle_message(_added_update(), context=None)
    team = TeamService(data_access).find_team_by_group_chat(GROUP)
    with team_context(team.doc_id):
        data_access.set_website('https://example.org')         # a fresh team may have touched settings

    await node_handler.handle_message(_removed_update(), context=None)

    with team_context(team.doc_id):
        assert not data_access.has_any_docs(Table.SETTINGS_TABLE)   # no orphaned subcollection docs

    assert TeamService(data_access).find_team_by_group_chat(GROUP) is None
    adder_state = data_access.get_user_state(ADDER_ID)
    assert adder_state.role == Role.INIT and adder_state.team_id is None
    assert current_state(data_access, ADDER_ID) == UserState.INIT
    assert any('cancelled' in t.lower() for t in bot.texts_to(ADDER_ID))
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    assert any('rolled back' in t for t in bot.texts_to(maintainer))
    assert_no_error_reported(bot)


async def test_removal_from_team_with_more_members_keeps_the_data(node_handler, data_access, bot, api_config):
    _make_adder_group_admin(bot)
    await node_handler.handle_message(_added_update(), context=None)
    team = TeamService(data_access).find_team_by_group_chat(GROUP)
    seed_user(data_access, ADDER_ID + 1, Role.PLAYER, UserState.DEFAULT, team_id=team.doc_id)

    await node_handler.handle_message(_removed_update(), context=None)

    assert TeamService(data_access).find_team_by_group_chat(GROUP) is not None
    assert data_access.get_user_state(ADDER_ID).is_admin                            # untouched
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    assert any('Data kept' in t for t in bot.texts_to(maintainer))
    assert_no_error_reported(bot)


async def test_teamless_start_shows_two_way_choice(node_handler, data_access, bot):
    bot.default_chat_member = ChatMemberLeft(user=User(id=1, first_name='x', is_bot=False))
    seed_user(data_access, ADDER_ID, Role.INIT, UserState.INIT, team_id='')

    await drive(node_handler, ADDER_ID, '/start')

    rejection = bot.sent[-1]
    button_data = [b.callback_data for row in rejection.reply_markup.inline_keyboard for b in row]
    assert OnboardingMenu.encode(OnboardingMenu.SPECTATOR) in button_data
    assert OnboardingMenu.encode(OnboardingMenu.NEW_TEAM) in button_data
    assert_no_error_reported(bot)


async def test_choice_buttons_explain_and_password_entry_still_joins(node_handler, data_access, bot,
                                                                     default_team):
    seed_user(data_access, ADDER_ID, Role.REJECTED, UserState.REJECTED, team_id='')

    update = await drive_callback(node_handler, ADDER_ID, OnboardingMenu.encode(OnboardingMenu.SPECTATOR))
    assert 'spectator password' in update.callback_query.edits[-1].text
    update = await drive_callback(node_handler, ADDER_ID, OnboardingMenu.encode(OnboardingMenu.NEW_TEAM))
    assert 'group chat' in update.callback_query.edits[-1].text

    await drive(node_handler, ADDER_ID, default_team.spectator_password)
    assert data_access.get_user_state(ADDER_ID).role == Role.SPECTATOR
    assert_no_error_reported(bot)


async def test_admin_renames_team_from_the_panel(node_handler, data_access, bot, default_team):
    seed_user(data_access, ADDER_ID, Role.PLAYER, UserState.DEFAULT, is_admin=True)
    await drive_callback(node_handler, ADDER_ID, AdminMenu.encode(AdminMenu.TEAM_NAME_PROMPT), message_id=88)
    await drive(node_handler, ADDER_ID, 'ZW Legends')

    await drive_callback(node_handler, ADDER_ID, AdminMenu.encode(AdminMenu.TEAM_NAME_SAVE))

    assert TeamService(data_access).get_team(default_team.doc_id).name == 'ZW Legends'
    assert current_state(data_access, ADDER_ID) == UserState.DEFAULT
    assert_no_error_reported(bot)


async def test_removal_keeps_team_whose_only_event_is_in_the_past(node_handler, data_access, bot, api_config):
    import datetime
    from data.TenantContext import team_context
    from domain.entities.Training import Training
    from domain.EventDateTimeParser import parse
    _make_adder_group_admin(bot)
    await node_handler.handle_message(_added_update(), context=None)
    team = TeamService(data_access).find_team_by_group_chat(GROUP)
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    with team_context(team.doc_id):
        data_access.add(Training(parse(f"{yesterday.strftime('%d.%m.%Y')} 19:00").value, 'old hall'))

    await node_handler.handle_message(_removed_update(), context=None)

    assert TeamService(data_access).find_team_by_group_chat(GROUP) is not None
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    assert any('Data kept' in t for t in bot.texts_to(maintainer))
    assert_no_error_reported(bot)


async def test_stale_team_name_save_never_commits_another_flows_staged_value(node_handler, data_access, bot,
                                                                             default_team):
    seed_user(data_access, ADDER_ID, Role.PLAYER, UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD,
              additional_info='88#1900#SuperSecret99', is_admin=True)

    update = await drive_callback(node_handler, ADDER_ID, AdminMenu.encode(AdminMenu.TEAM_NAME_SAVE))

    assert TeamService(data_access).get_team(default_team.doc_id).name == default_team.name
    assert 'no longer active' in update.callback_query.edits[-1].text
    staged = data_access.get_user_state(ADDER_ID)
    assert staged.state == UserState.ADMIN_UPDATE_SPECTATOR_PASSWORD      # other flow untouched
    assert 'SuperSecret99' in staged.additional_info
    assert_no_error_reported(bot)
