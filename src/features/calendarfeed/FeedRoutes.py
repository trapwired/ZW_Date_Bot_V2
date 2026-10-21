"""The calendar feed's public HTTP surface (plan §6): the calendar app's poll and a
liveness probe. Unauthenticated - the token in the path is the only credential, so
every kind of miss answers the identical 404 and reveals nothing."""
import asyncio
import logging

from aiohttp import web

NOT_FOUND_TEXT = ('Dieser Kalender-Link gilt nicht mehr. Im Bot unter Termine → 📆 gibt es einen neuen. / '
                  'This calendar link is no longer valid; get a new one in the bot under Events → 📆.\n')
SERVER_ERROR_TEXT = 'The calendar could not be built right now; please try again later.\n'
FEED_DOWNLOAD_NAME = 'zw-date-bot.ics'

# Each render holds one connection of the Postgres pool, which has 4 and is shared with the bot's
# handlers: capped at 2 so a burst of polls queues here instead of starving Telegram handling.
CONCURRENT_FEED_RENDERS = asyncio.Semaphore(2)


def _not_found() -> web.Response:
    return web.Response(status=404, text=NOT_FOUND_TEXT, content_type='text/plain', charset='utf-8',
                        headers={'Cache-Control': 'no-store'})


def build_feed_app(calendar_feed_service) -> web.Application:
    async def serve_feed(request: web.Request) -> web.Response:
        try:
            # The repository is sync; on the bot's shared loop a slow query must not
            # freeze Telegram handling.
            async with CONCURRENT_FEED_RENDERS:
                body = await asyncio.to_thread(calendar_feed_service.render_feed, request.match_info['file'])
        except Exception:
            # Logged only, no maintainer Telegram alert: a broken feed would page on
            # every poll. The heartbeat / uptime check is the alert.
            logging.exception('Calendar feed request failed')
            return web.Response(status=500, text=SERVER_ERROR_TEXT, content_type='text/plain', charset='utf-8')
        if body is None:
            return _not_found()
        return web.Response(text=body, content_type='text/calendar', charset='utf-8',
                            headers={'Cache-Control': 'no-cache',
                                     'Content-Disposition': f'inline; filename="{FEED_DOWNLOAD_NAME}"'})

    async def not_found(_request: web.Request) -> web.Response:
        return _not_found()

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text='ok', content_type='text/plain')

    app = web.Application()
    app.router.add_get('/cal/{file}', serve_feed)
    # Everything else under /cal/ (empty, nested, trailing slash, other methods) is the same 404
    # as a wrong token. Registered after the feed route, which wins for a plain GET.
    app.router.add_route('*', '/cal/{tail:.*}', not_found)
    app.router.add_get('/healthz', health)
    return app
