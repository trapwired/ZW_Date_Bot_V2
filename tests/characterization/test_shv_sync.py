"""Characterization: the SHV schedule sync end to end - the daily job's automatic
updates and admin questions, and the full button/reason flows through the real
NodeHandler, on the in-memory backend with a faked SHV feed."""
from types import SimpleNamespace

import pandas as pd
import pytest

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role
from Enums.UserState import UserState

from domain.entities.Game import Game

from features.shvsync import ShvApiClient
from features.shvsync.ShvApiClient import ShvGame

from Utils import DateTimeUtils

from tests.helpers import (seed_user, set_attendance, drive, drive_callback,
                           assert_no_error_reported, current_state)

ADMIN_ID = 5001
PLAYER_ID = 5002
SHV_TEAM_ID = 41317


def _ts(day: int, hour: int = 18) -> pd.Timestamp:
    return DateTimeUtils.add_zurich_timezone(pd.Timestamp(2030, 11, day, hour, 30))


def _shv_game(shv_game_id=501, day=1, hour=18, opponent='HC Arbon 3', location='Uzwil bzu'):
    return ShvGame(shv_game_id=shv_game_id, timestamp=_ts(day, hour),
                   opponent=opponent, location=location, is_played=False)


def _messages_to(bot, chat_id):
    return [m for m in bot.sent if m.chat_id == chat_id]


def _question_tokens(bot, chat_id):
    """The SHV#-button callback datas of every question message sent to chat_id."""
    datas = []
    for message in _messages_to(bot, chat_id):
        markup = message.reply_markup
        if markup is not None and getattr(markup, 'inline_keyboard', None):
            data = markup.inline_keyboard[0][0].callback_data
            if data.startswith('SHV#'):
                datas.append(data)
    return datas


@pytest.fixture
def sync(node_handler, data_access, bot, monkeypatch):
    """The sync service the callbacks are wired to, plus a mutable fake SHV feed,
    a seeded admin and a seeded player."""
    feed = []

    async def fake_fetch_games(shv_team_id):
        return list(feed)

    monkeypatch.setattr(ShvApiClient, 'fetch_games', fake_fetch_games)
    data_access.set_website(f'https://www.handball.ch/de/matchcenter/teams/{SHV_TEAM_ID}#/games')
    seed_user(data_access, ADMIN_ID, Role.PLAYER, UserState.DEFAULT, first_name='Admin',
              is_admin=True)
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT, first_name='Player')

    async def run():
        await node_handler.shv_sync_service.sync_all_teams(context=None)

    return SimpleNamespace(run=run, feed=feed, node_handler=node_handler,
                           data_access=data_access, bot=bot)


def _as_no(yes_callback_data: str) -> str:
    # encode() appends the team stamp, so the answer is the middle segment:
    # SHV#<token>#Y#t:<team> -> SHV#<token>#N#t:<team>
    return yes_callback_data.replace('#Y#', '#N#')


###################
# AUTOMATIC PATHS #
###################

async def test_team_without_website_is_skipped_silently(sync):
    sync.data_access.set_website(None)
    sync.feed.append(_shv_game())

    await sync.run()

    assert sync.data_access.get_ordered_games() == []
    assert sync.bot.sent == []


async def test_non_matchcenter_website_alerts_the_maintainer_with_a_disable_button(sync, api_config):
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    seed_user(sync.data_access, maintainer, Role.PLAYER, UserState.DEFAULT,
              first_name='Maintainer', is_admin=True)
    sync.data_access.set_website('https://zueri-west.ch')
    sync.feed.append(_shv_game())

    await sync.run()

    alerts = _messages_to(sync.bot, maintainer)
    assert len(alerts) == 1
    assert 'zueri-west.ch' in alerts[0].text
    assert alerts[0].reply_markup is not None
    disable_data = alerts[0].reply_markup.inline_keyboard[0][0].callback_data

    await drive_callback(sync.node_handler, maintainer, disable_data)
    await sync.run()

    # Disabled: the second sync neither re-alerts nor touches anything.
    assert len(_messages_to(sync.bot, maintainer)) == 1
    assert sync.data_access.get_ordered_games() == []
    assert_no_error_reported(sync.bot)


async def test_disable_button_is_inert_for_anyone_but_the_maintainer(sync, api_config):
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    seed_user(sync.data_access, maintainer, Role.PLAYER, UserState.DEFAULT,
              first_name='Maintainer', is_admin=True)
    sync.data_access.set_website('https://zueri-west.ch')
    await sync.run()
    disable_data = _messages_to(sync.bot, maintainer)[0].reply_markup.inline_keyboard[0][0].callback_data

    update = await drive_callback(sync.node_handler, ADMIN_ID, disable_data)

    assert update.callback_query.edits == []
    await sync.run()
    assert len(_messages_to(sync.bot, maintainer)) == 2  # still enabled - alerted again
    assert_no_error_reported(sync.bot)


async def test_empty_feed_with_future_bot_games_alerts_instead_of_asking_deletions(sync, api_config):
    # The SHV mints a new team id every season: a stale website answers with only
    # played games. That must never turn into a wave of delete questions.
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))

    await sync.run()

    assert _question_tokens(sync.bot, ADMIN_ID) == []
    assert len(sync.data_access.get_ordered_games()) == 1
    alerts = _messages_to(sync.bot, maintainer)
    assert len(alerts) == 1
    assert 'season' in alerts[0].text and 'matchcenter/teams/41317' in alerts[0].text
    assert alerts[0].reply_markup is not None  # disable button
    assert_no_error_reported(sync.bot)


async def test_fetch_failure_alerts_the_maintainer_with_website_and_tried_path(sync, api_config,
                                                                               monkeypatch):
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))

    async def broken_fetch(shv_team_id):
        raise ShvApiClient.ShvApiError('unexpected SHV response')

    monkeypatch.setattr(ShvApiClient, 'fetch_games', broken_fetch)

    await sync.run()

    alerts = [m.text for m in _messages_to(sync.bot, maintainer)]
    assert len(alerts) == 1
    assert 'matchcenter/teams/41317' in alerts[0]  # the stored website
    assert 'Umbraco/Api/MatchCenter/Query' in alerts[0]  # the tried path
    assert f'teamId={SHV_TEAM_ID}' in alerts[0]
    assert_no_error_reported(sync.bot)


async def test_move_over_two_hours_is_applied_resets_answers_and_notifies_players(sync):
    game = sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    user_doc_id = sync.data_access.get_user(PLAYER_ID).doc_id
    set_attendance(sync.data_access, user_doc_id, game.doc_id, AttendanceState.YES)
    sync.feed.append(_shv_game(day=8))

    await sync.run()

    games = sync.data_access.get_ordered_games()
    assert games[0].doc_id == game.doc_id and games[0].timestamp == _ts(8)
    assert sync.data_access.get_attendance(PLAYER_ID, game.doc_id, Event.GAME).state \
        == AttendanceState.UNSURE
    assert len(_messages_to(sync.bot, PLAYER_ID)) == 2  # moved intro + attendance card
    # The admin is a player too: push (intro + card) plus the sync report.
    admin_messages = _messages_to(sync.bot, ADMIN_ID)
    assert len(admin_messages) == 3
    assert any('Game changed' in message.text for message in admin_messages)
    assert_no_error_reported(sync.bot)


async def test_small_move_is_applied_silently_with_admin_report_only(sync):
    game = sync.data_access.add(Game(_ts(1, 18), 'Uzwil bzu', 'HC Arbon 3', 501))
    user_doc_id = sync.data_access.get_user(PLAYER_ID).doc_id
    set_attendance(sync.data_access, user_doc_id, game.doc_id, AttendanceState.YES)
    sync.feed.append(_shv_game(day=1, hour=19))

    await sync.run()

    assert sync.data_access.get_ordered_games()[0].timestamp == _ts(1, 19)
    assert sync.data_access.get_attendance(PLAYER_ID, game.doc_id, Event.GAME).state \
        == AttendanceState.YES
    assert _messages_to(sync.bot, PLAYER_ID) == []
    assert len(_messages_to(sync.bot, ADMIN_ID)) == 1
    assert_no_error_reported(sync.bot)


async def test_unchanged_feed_stays_silent(sync):
    sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    sync.feed.append(_shv_game())

    await sync.run()

    assert sync.bot.sent == []


##################
# CREATE (1 new) #
##################

async def test_create_question_yes_imports_the_game_and_notifies_players(sync):
    sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    sync.feed.extend([_shv_game(), _shv_game(shv_game_id=502, day=15, opponent='HC Romanshorn')])

    await sync.run()
    tokens = _question_tokens(sync.bot, ADMIN_ID)
    assert len(tokens) == 1

    update = await drive_callback(sync.node_handler, ADMIN_ID, tokens[0])  # first button = Yes

    games = sorted(sync.data_access.get_ordered_games(), key=lambda g: g.timestamp)
    assert [game.shv_game_id for game in games] == [501, 502]
    assert 'added' in update.callback_query.edits[-1].text
    assert len(_messages_to(sync.bot, PLAYER_ID)) == 2  # new-game intro + attendance card
    assert_no_error_reported(sync.bot)


async def test_second_press_finds_the_question_already_answered(sync):
    sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    sync.feed.extend([_shv_game(), _shv_game(shv_game_id=502, day=15, opponent='HC Romanshorn')])
    await sync.run()
    token = _question_tokens(sync.bot, ADMIN_ID)[0]
    await drive_callback(sync.node_handler, ADMIN_ID, token)

    update = await drive_callback(sync.node_handler, ADMIN_ID, token)

    assert 'already answered' in update.callback_query.edits[-1].text
    assert len(sync.data_access.get_ordered_games()) == 2  # not created twice
    assert_no_error_reported(sync.bot)


async def test_create_question_no_asks_for_a_reason_and_reports_the_maintainer(sync, api_config):
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    sync.feed.extend([_shv_game(), _shv_game(shv_game_id=502, day=15, opponent='HC Romanshorn')])
    await sync.run()
    yes_data = _question_tokens(sync.bot, ADMIN_ID)[0]
    no_data = _as_no(yes_data)

    update = await drive_callback(sync.node_handler, ADMIN_ID, no_data)
    assert 'reason' in update.callback_query.edits[-1].text
    assert current_state(sync.data_access, ADMIN_ID) == UserState.SHV_DECLINE_REASON
    await drive(sync.node_handler, ADMIN_ID, 'second team plays that day')

    assert current_state(sync.data_access, ADMIN_ID) == UserState.DEFAULT
    maintainer_texts = [m.text for m in _messages_to(sync.bot, maintainer)]
    assert any('declined CREATE' in text for text in maintainer_texts)
    assert any('second team plays that day' in text for text in maintainer_texts)
    assert len(sync.data_access.get_ordered_games()) == 1  # nothing imported

    admin_questions_before = len(_question_tokens(sync.bot, ADMIN_ID))
    await sync.run()
    assert len(_question_tokens(sync.bot, ADMIN_ID)) == admin_questions_before  # not re-asked
    assert_no_error_reported(sync.bot)


async def test_declined_question_is_asked_again_after_the_reask_window(sync):
    sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    sync.feed.extend([_shv_game(), _shv_game(shv_game_id=502, day=15, opponent='HC Romanshorn')])
    await sync.run()
    no_data = _as_no(_question_tokens(sync.bot, ADMIN_ID)[0])
    await drive_callback(sync.node_handler, ADMIN_ID, no_data)

    decision = sync.data_access.get_shv_sync_decisions()[0]
    decision.asked_at = decision.asked_at - pd.Timedelta(days=15)
    sync.data_access.update(decision)
    before = len(_question_tokens(sync.bot, ADMIN_ID))
    await sync.run()

    assert len(_question_tokens(sync.bot, ADMIN_ID)) == before + 1
    assert_no_error_reported(sync.bot)


#########
# ADOPT #
#########

async def test_adopt_question_yes_links_the_manual_game_to_the_shv_data(sync):
    manual = sync.data_access.add(Game(_ts(1, 17), 'Uzwil bzu', 'Arbon', None))
    sync.feed.append(_shv_game(day=1, hour=18))

    await sync.run()
    tokens = _question_tokens(sync.bot, ADMIN_ID)
    assert len(tokens) == 1

    update = await drive_callback(sync.node_handler, ADMIN_ID, tokens[0])

    games = sync.data_access.get_ordered_games()
    assert len(games) == 1
    assert games[0].doc_id == manual.doc_id
    assert games[0].shv_game_id == 501
    assert games[0].opponent == 'HC Arbon 3'  # SHV spelling wins, stable across seasons
    assert 'mirrors the SHV schedule' in update.callback_query.edits[-1].text
    assert_no_error_reported(sync.bot)


async def test_adopt_question_no_is_final_and_the_next_sync_splits_the_pair(sync, api_config):
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    sync.data_access.add(Game(_ts(1, 17), 'Uzwil bzu', 'Arbon', None))
    sync.feed.append(_shv_game(day=1, hour=18))
    await sync.run()
    no_data = _as_no(_question_tokens(sync.bot, ADMIN_ID)[0])

    update = await drive_callback(sync.node_handler, ADMIN_ID, no_data)

    assert 'different games' in update.callback_query.edits[-1].text
    assert current_state(sync.data_access, ADMIN_ID) == UserState.DEFAULT  # no reason flow
    assert any('declined ADOPT' in m.text for m in _messages_to(sync.bot, maintainer))

    before = len(_question_tokens(sync.bot, ADMIN_ID))
    await sync.run()
    # The pair is final: the SHV game is now a create question, the bot game a
    # delete-or-keep question - but the same-game question never returns.
    assert len(_question_tokens(sync.bot, ADMIN_ID)) == before + 2
    assert_no_error_reported(sync.bot)


##########
# DELETE #
##########

async def test_vanished_question_yes_deletes_the_game(sync):
    sync.data_access.add(Game(_ts(2), 'Uzwil bzu', 'HC Romanshorn', 502))
    game = sync.data_access.add(Game(_ts(1), 'Uzwil bzu', 'HC Arbon 3', 501))
    user_doc_id = sync.data_access.get_user(PLAYER_ID).doc_id
    set_attendance(sync.data_access, user_doc_id, game.doc_id, AttendanceState.YES)
    sync.feed.append(_shv_game(shv_game_id=502, day=2, opponent='HC Romanshorn'))  # 501 vanished

    await sync.run()
    tokens = _question_tokens(sync.bot, ADMIN_ID)
    assert len(tokens) == 1

    update = await drive_callback(sync.node_handler, ADMIN_ID, tokens[0])

    assert [g.shv_game_id for g in sync.data_access.get_ordered_games()] == [502]
    assert 'deleted' in update.callback_query.edits[-1].text
    assert_no_error_reported(sync.bot)


async def test_manual_game_kept_with_reason_is_never_asked_about_again(sync, api_config):
    maintainer = int(api_config.get_key('Chat_Ids', 'MAINTAINER'))
    sync.data_access.add(Game(_ts(2), 'Uzwil bzu', 'HC Arbon 3', 501))
    sync.data_access.add(Game(_ts(1), 'own hall', 'Friendly FC', None))
    sync.feed.append(_shv_game(day=2))

    await sync.run()
    no_data = _as_no(_question_tokens(sync.bot, ADMIN_ID)[0])
    await drive_callback(sync.node_handler, ADMIN_ID, no_data)
    await drive(sync.node_handler, ADMIN_ID, 'friendly game, not on SHV')

    assert any('friendly game, not on SHV' in m.text for m in _messages_to(sync.bot, maintainer))
    before = len(_question_tokens(sync.bot, ADMIN_ID))
    await sync.run()
    await sync.run()

    assert len(_question_tokens(sync.bot, ADMIN_ID)) == before  # final - never re-asked
    assert len(sync.data_access.get_ordered_games()) == 2  # and the friendly stays
    assert_no_error_reported(sync.bot)


###############
# BULK IMPORT #
###############

async def test_empty_schedule_gets_one_bulk_question_and_yes_imports_everything(sync):
    sync.feed.extend([_shv_game(), _shv_game(shv_game_id=502, day=15, opponent='HC Romanshorn'),
                      _shv_game(shv_game_id=503, day=22, opponent='HC Rheintal 2')])

    await sync.run()
    tokens = _question_tokens(sync.bot, ADMIN_ID)
    assert len(tokens) == 1  # ONE question, not three

    update = await drive_callback(sync.node_handler, ADMIN_ID, tokens[0])

    games = sync.data_access.get_ordered_games()
    assert sorted(game.shv_game_id for game in games) == [501, 502, 503]
    assert 'Imported 3 games' in update.callback_query.edits[-1].text
    assert len(_messages_to(sync.bot, PLAYER_ID)) == 4  # one intro + three attendance cards
    assert_no_error_reported(sync.bot)
