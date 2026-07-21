"""Dead-man ping for the polling bot: no HTTP endpoint exists, so liveness is proven
actively - a job on the bot's own event loop pings healthchecks.io. If the process,
the loop or the job queue silently dies, the ping stops and the check alerts
(alert on absence of success - the box cannot report its own death)."""
import logging
import os

import httpx

HEALTHCHECK_URL_ENV = 'HEALTHCHECK_URL'
PING_INTERVAL_SECONDS = 300


def register(job_queue) -> bool:
    """Wire the ping job; no-op (False) when HEALTHCHECK_URL is unset, so local
    runs and tests need no configuration."""
    url = os.environ.get(HEALTHCHECK_URL_ENV)
    if not url:
        logging.info('%s not set - dead-man ping disabled', HEALTHCHECK_URL_ENV)
        return False

    async def ping(context):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(url)
        except httpx.HTTPError as e:
            # Transient network noise must not kill the job; the check's grace
            # period covers gaps, sustained failure alerts by absence.
            logging.warning('healthcheck ping failed: %s', e)

    job_queue.run_repeating(ping, interval=PING_INTERVAL_SECONDS, first=10)
    return True
