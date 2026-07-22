"""Contract-test harness: every test in this directory runs against BOTH storage
backends - InMemoryRepository (the double the whole test suite runs on) and
PostgresRepository on a real Postgres - so the seam's semantics cannot drift
between them. This is what makes the in-memory double trustworthy: any behavior
the characterization tests rely on is pinned to the production backend here.

Postgres comes from POSTGRES_TEST_DSN (CI provides a service container; locally
`docker run -d -p 5433:5432 -e POSTGRES_USER=zwdatebot -e POSTGRES_PASSWORD=zwdatebot
-e POSTGRES_DB=zwdatebot_test postgres:16` does it). Without a reachable server the
postgres half SKIPS, so the plain suite stays runnable anywhere.
"""
import os

import pytest

from data.TenantContext import set_current_team, reset_current_team
from domain.entities.Team import Team
from Enums.Table import Table

POSTGRES_TEST_DSN = os.environ.get(
    'POSTGRES_TEST_DSN', 'postgresql://zwdatebot:zwdatebot@localhost:5433/zwdatebot_test')


class _DsnOnlyConfig:
    def get_key(self, section, identifier, default=None):
        return POSTGRES_TEST_DSN if identifier == 'dsn' else default


def _in_memory_repository(api_config):
    from tests.doubles.in_memory_repository import InMemoryRepository
    from data.Tables import Tables
    return InMemoryRepository(Tables(api_config))


def _postgres_repository():
    psycopg = pytest.importorskip('psycopg')
    try:
        with psycopg.connect(POSTGRES_TEST_DSN, connect_timeout=2):
            pass
    except psycopg.OperationalError:
        pytest.skip(f'no Postgres at {POSTGRES_TEST_DSN} - start one or set POSTGRES_TEST_DSN')
    from data.PostgresRepository import PostgresRepository
    return PostgresRepository(_DsnOnlyConfig())


def _truncate_all(repository):
    from data.PostgresRepository import TABLE_SPECS
    tables = ', '.join({spec.sql_table for spec in TABLE_SPECS.values()})
    repository._execute(f'TRUNCATE {tables}')


@pytest.fixture(params=['inmemory', 'postgres'])
def repository(request, api_config):
    if request.param == 'inmemory':
        repo = _in_memory_repository(api_config)
    else:
        repo = _postgres_repository()
        _truncate_all(repo)

    team_id = repo.add(Team('Contract FC', group_chat_id=-100123, spectator_password='secret-pass'),
                       Table.TEAMS_TABLE)
    token = set_current_team(team_id)
    try:
        yield repo
    finally:
        reset_current_team(token)
        if request.param == 'postgres':
            repo.pool.close()
