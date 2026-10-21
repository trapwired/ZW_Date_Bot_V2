"""Feature-agnostic HTTP ingress: serves an aiohttp app on the bot's own event loop.
main.py starts it from PTB's post_init and stops it in post_shutdown, so it shares
run_polling's loop and the bot's process lifetime (plan §4, option A)."""
import logging

from aiohttp import web


class HttpServer:

    def __init__(self, app: web.Application, port: int, host: str = '0.0.0.0'):
        self.app = app
        self.port = port
        self.host = host
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        # handle_signals=False: PTB's run_polling owns SIGINT/SIGTERM.
        # No request line in the access log: paths can carry credentials (calendar tokens).
        runner = web.AppRunner(self.app, handle_signals=False, access_log_format='%a %s %b %Tf')
        await runner.setup()
        try:
            await web.TCPSite(runner, self.host, self.port).start()
        except OSError:
            # A taken port must not take the bot down with it (plan §4): only the HTTP surface is lost,
            # which the hand-off's switch-on checks (curl the feed) and the uptime probe catch.
            logging.error('HTTP server could not bind %s:%s - calendar feed is down, bot keeps running',
                          self.host, self.port, exc_info=True)
            await runner.cleanup()
            return
        self._runner = runner
        logging.info('HTTP server listening on %s:%s', self.host, self.port)

    async def stop(self) -> None:
        if self._runner is None:
            return
        await self._runner.cleanup()
        self._runner = None
