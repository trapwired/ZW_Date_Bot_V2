"""THE per-team wrapper for scheduled jobs: every job body runs once per team,
inside that team's tenant and language context. Extracted from SchedulingService
so other slices' scheduled jobs (e.g. the SHV schedule sync) cannot drift from
its semantics."""
from data.DataAccess import DataAccess
from data.TenantContext import team_context

from localization.LanguageContext import language_context
from localization.Languages import DEFAULT_LANGUAGE


async def for_each_team(data_access: DataAccess, telegram_service, job_body, *args):
    """Run job_body once per team, inside that team's tenant context, so all reads
    inside the body are team-scoped. The loop itself guarantees one team's failure
    cannot skip the remaining teams - it does not rely on each body catching its
    own errors."""
    try:
        teams = data_access.get_all_teams()
    except Exception as e:
        await telegram_service.report_exception('Exception listing teams for scheduled job', e)
        return
    for team in teams:
        # The team's language is the ambient default for this iteration (group
        # summaries, trainer messages); per-recipient DM sends override it.
        # getattr: fail open for team doubles/docs without the field.
        with team_context(team.doc_id), language_context(getattr(team, 'language', DEFAULT_LANGUAGE)):
            try:
                await job_body(*args)
            except Exception as e:
                await telegram_service.report_exception(
                    f'Exception in scheduled job for team {team.doc_id}', e)
