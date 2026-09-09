"""Unit: _send_message BadRequest 'Chat not found' handling.

A stale trainer chat id (deleted group, mistyped id) raises BadRequest, which
previously aborted send_info_message_to_trainers mid-loop and surfaced as a
maintainer ERROR stack dump. It must instead be reported as an INFO notice
naming the chat id, and the remaining recipients must still be served. Any
other BadRequest (e.g. broken markup - a caller bug) must keep propagating.
"""
import pytest
from telegram.error import BadRequest

from Enums.Event import Event
from domain.entities.Team import Team
from data.TenantContext import team_context
from tests.helpers import make_chat_unknown

STALE_TRAINER = 922000001
HEALTHY_TRAINER = 922000002
GROUP = -100777666


async def test_chat_not_found_reports_and_continues_with_remaining_trainers(services, data_access, bot,
                                                                            api_config):
    team = data_access.add(Team('Berg', group_chat_id=GROUP,
                                trainers_training=[STALE_TRAINER, HEALTHY_TRAINER]))
    make_chat_unknown(bot, STALE_TRAINER)

    with team_context(team.doc_id):
        await services["telegram_service"].send_info_message_to_trainers('summary', Event.TRAINING)

    assert bot.texts_to(HEALTHY_TRAINER) == ['summary']
    maintainer_texts = bot.texts_to(int(api_config.get_key('Chat_Ids', 'MAINTAINER')))
    assert len(maintainer_texts) == 1
    assert 'Chat not found' in maintainer_texts[0] and str(STALE_TRAINER) in maintainer_texts[0]
    assert '⚠️ ERROR' not in maintainer_texts[0]


async def test_stale_chat_id_is_not_auto_removed_from_team(services, data_access, bot, api_config):
    team = data_access.add(Team('Berg', group_chat_id=GROUP, trainers_training=[STALE_TRAINER]))
    make_chat_unknown(bot, STALE_TRAINER)

    with team_context(team.doc_id):
        await services["telegram_service"].send_info_message_to_trainers('summary', Event.TRAINING)

    # Report-only by design: the roster is admin-owned data, the bot must not edit it.
    assert data_access.get_team(team.doc_id).trainers_training == [STALE_TRAINER]


async def test_other_bad_request_still_propagates(services, bot):
    make_chat_unknown(bot, STALE_TRAINER, error_message="Can't parse entities")

    with pytest.raises(BadRequest):
        await services["telegram_service"]._send_message(chat_id=STALE_TRAINER, message='hi')
