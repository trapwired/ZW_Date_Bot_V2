"""HttpServer lifecycle as main.py drives it (post_init / post_shutdown), and the
access log that must never carry a request path (calendar tokens live in it)."""
import logging
import socket

import aiohttp
from aiohttp import web
from aiohttp.test_utils import unused_port

from framework.HttpServer import HttpServer

SECRET_PATH = '/cal/' + 'S' * 40 + '.ics'


def _app() -> web.Application:
    async def handler(_request):
        return web.Response(text='served')

    app = web.Application()
    app.router.add_get('/cal/{file}', handler)
    return app


async def test_serves_until_stopped_and_logs_no_paths(caplog):
    port = unused_port()
    server = HttpServer(_app(), port, host='127.0.0.1')

    await server.start()
    try:
        with caplog.at_level(logging.INFO, logger='aiohttp.access'):
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://127.0.0.1:{port}{SECRET_PATH}') as response:
                    body = await response.text()
    finally:
        await server.stop()

    assert body == 'served'
    access_lines = [record.getMessage() for record in caplog.records if record.name == 'aiohttp.access']
    assert access_lines, 'the access log itself stays on'
    assert not any('/cal/' in line or 'S' * 40 in line for line in access_lines)


async def test_taken_port_is_logged_and_does_not_stop_the_bot(caplog):
    with socket.socket() as other_listener:
        other_listener.bind(('127.0.0.1', 0))
        other_listener.listen()
        port = other_listener.getsockname()[1]
        server = HttpServer(_app(), port, host='127.0.0.1')

        with caplog.at_level(logging.ERROR):
            await server.start()
        await server.stop()

    assert f'HTTP server could not bind 127.0.0.1:{port}' in caplog.text
    assert server._runner is None


async def test_stop_without_start_is_a_no_op():
    await HttpServer(_app(), unused_port()).stop()
