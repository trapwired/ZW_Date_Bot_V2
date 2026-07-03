"""Per-team message routing (multi-team PR 3/3).

Scheduled jobs iterate all teams; inside each team's tenant context the group
reminder must land in THAT team's group chat and the trainer summary must go to
THAT team's trainers - never across. A team without configured trainers falls
back to its own group chat.
"""
import datetime

from Enums.Event import Event
from domain.entities.Team import Team
from domain.entities.Training import Training
from domain.EventDateTimeParser import parse
from data.TenantContext import team_context

TEAM_B_GROUP = -200999888


def _training_in_days(data_access, days: int, location: str):
    day = datetime.date.today() + datetime.timedelta(days=days)
    return data_access.add(Training(parse(f"{day.strftime('%d.%m.%Y')} 19:00").value, location))


async def test_group_reminder_goes_to_each_teams_own_group_chat(services, data_access, bot, default_team):
    team_b = data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP))
    _training_in_days(data_access, days=1, location='zueri hall')
    with team_context(team_b.doc_id):
        _training_in_days(data_access, days=1, location='berg hall')

    await services["scheduling_service"].send_previous_day_training_reminder(context=None)

    zw_texts = bot.texts_to(default_team.group_chat_id)
    berg_texts = bot.texts_to(TEAM_B_GROUP)
    assert len(zw_texts) == 1 and 'Zueri Hall' in zw_texts[0]
    assert len(berg_texts) == 1 and 'Berg Hall' in berg_texts[0]


async def test_trainer_summary_goes_to_own_trainers_or_falls_back_to_group_chat(services, data_access, bot,
                                                                                default_team):
    scheduling = services["scheduling_service"]
    summary_day = scheduling.get_summary_reminder_day(Event.TRAINING)[0]
    team_b = data_access.add(Team('Berg', group_chat_id=TEAM_B_GROUP))  # no trainers configured
    _training_in_days(data_access, days=summary_day, location='zueri hall')
    with team_context(team_b.doc_id):
        _training_in_days(data_access, days=summary_day, location='berg hall')

    await scheduling.send_training_summary(context=None)

    trainer_texts = bot.texts_to(default_team.trainers_training[0])
    berg_texts = bot.texts_to(TEAM_B_GROUP)
    assert len(trainer_texts) == 1 and 'Zueri Hall' in trainer_texts[0]
    assert len(berg_texts) == 1 and 'Berg Hall' in berg_texts[0]
    assert bot.texts_to(default_team.group_chat_id) == []
