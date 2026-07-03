"""Unit: _send_message Forbidden handling.

Trainer routing can now target a GROUP chat (the no-trainers fallback in
Team.trainer_chat_ids). A group id has no users_to_state doc, so the Forbidden
handler must not try to deactivate it - only report to the maintainer.
"""
from telegram.error import Forbidden

from Enums.Event import Event
from Enums.Role import Role
from Enums.UserState import UserState
from domain.entities.Team import Team
from data.TenantContext import team_context
from tests.helpers import seed_user

GROUP = -100777666


def _forbid_chat(bot, forbidden_chat_id):
    original = bot.send_message

    async def send(chat_id, text, reply_markup=None, parse_mode=None):
        if chat_id == forbidden_chat_id:
            raise Forbidden('bot was kicked')
        return await original(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    bot.send_message = send


async def test_forbidden_group_fallback_reports_without_touching_user_state(services, data_access, bot,
                                                                             api_config):
    team_b = data_access.add(Team('Berg', group_chat_id=GROUP))  # no trainers -> group fallback
    _forbid_chat(bot, GROUP)

    with team_context(team_b.doc_id):
        await services["telegram_service"].send_info_message_to_trainers('summary', Event.TRAINING)

    maintainer_texts = bot.texts_to(int(api_config.get_key('Chat_Ids', 'MAINTAINER')))
    assert len(maintainer_texts) == 1 and 'Forbidden' in maintainer_texts[0]


async def test_forbidden_user_is_still_set_inactive(services, data_access, bot, api_config):
    user_id = 555001
    seed_user(data_access, user_id, Role.PLAYER, UserState.DEFAULT)
    _forbid_chat(bot, user_id)

    await services["telegram_service"]._send_message(chat_id=user_id, message='hi')

    assert data_access.get_user_state(user_id).role == Role.INACTIVE
    maintainer_texts = bot.texts_to(int(api_config.get_key('Chat_Ids', 'MAINTAINER')))
    assert len(maintainer_texts) == 1 and 'Setting User to Inactive' in maintainer_texts[0]
