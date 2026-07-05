"""Characterization: the per-user language switch end to end (ADR 0004).

/language shows the picker, picking persists + answers in the new language,
localized keyboard labels still route, and the client language seeds the
profile on first contact.
"""
from datetime import datetime, timedelta

from telegram import Update, Message, Chat, User
from telegram.constants import ChatType

from Enums.Role import Role
from Enums.UserState import UserState

from tests.helpers import drive, drive_callback, seed_user, assert_no_error_reported

PLAYER_ID = 1500


async def test_language_picker_lists_all_native_names(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive(node_handler, PLAYER_ID, '/language')

    picker = [m for m in bot.sent if m.chat_id == PLAYER_ID][-1]
    assert 'Which language should I talk to you in?' in picker.text
    labels = [button.text for row in picker.reply_markup.inline_keyboard for button in row]
    assert labels == ['✅ English', 'Deutsch', 'Züridütsch', 'Français', 'Italiano']
    assert_no_error_reported(bot)


async def test_picking_a_language_persists_and_answers_in_it(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)

    await drive_callback(node_handler, PLAYER_ID, 'LANG#de')

    assert data_access.get_user_state(PLAYER_ID).language == 'de'
    confirmation = bot.texts_to(PLAYER_ID)[-1]
    assert confirmation == 'Sprache aktualisiert 👍'
    assert_no_error_reported(bot)


async def test_localized_keyboard_label_still_routes(node_handler, data_access, bot):
    user = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    user.language = 'de'
    data_access.update(user)

    # Telegram echoes the German button label back as plain text.
    await drive(node_handler, PLAYER_ID, 'Termine')

    assert 'Zurzeit stehen keine Events an.' in bot.texts_to(PLAYER_ID)[-1]
    assert_no_error_reported(bot)


async def test_client_language_seeds_profile_on_first_contact(node_handler, data_access, bot):
    seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    chat = Chat(id=PLAYER_ID, type=ChatType.PRIVATE)
    swiss_client = User(id=PLAYER_ID, first_name='Test', last_name='User', is_bot=False,
                        language_code='de-CH')
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=swiss_client, text='help')

    await node_handler.handle_message(Update(update_id=1, message=message), context=None)

    # Snapshot: the client language is now stored, so fan-out sends can use it.
    assert data_access.get_user_state(PLAYER_ID).language == 'de'
    assert 'Hier sind meine verfügbaren Befehle:' in bot.texts_to(PLAYER_ID)[-1]
    assert_no_error_reported(bot)


async def test_group_summary_speaks_the_team_language(services, data_access, default_team, bot):
    from domain.entities.Game import Game
    default_team.language = 'de'
    data_access.update(default_team)
    # Later today: still in the future (get_ordered_games filters past events) but
    # matching the same-day reminder window.
    data_access.add(Game(datetime.now() + timedelta(minutes=5), 'home arena', 'rivals fc'))

    await services['scheduling_service'].send_same_day_game_reminder(None)

    group_messages = [m for m in bot.sent if m.chat_id == default_team.group_chat_id]
    assert group_messages, 'expected a same-day game summary in the group chat'
    assert 'Heute Spiel!' in group_messages[-1].text


async def test_explicit_choice_beats_client_language(node_handler, data_access, bot):
    user = seed_user(data_access, PLAYER_ID, Role.PLAYER, UserState.DEFAULT)
    user.language = 'it'
    data_access.update(user)
    chat = Chat(id=PLAYER_ID, type=ChatType.PRIVATE)
    swiss_client = User(id=PLAYER_ID, first_name='Test', last_name='User', is_bot=False,
                        language_code='de-CH')
    message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=swiss_client, text='help')

    await node_handler.handle_message(Update(update_id=1, message=message), context=None)

    assert 'Ecco i miei comandi disponibili:' in bot.texts_to(PLAYER_ID)[-1]
    assert data_access.get_user_state(PLAYER_ID).language == 'it'  # not overwritten
    assert_no_error_reported(bot)
