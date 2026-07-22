"""Resolves which storage backend runs, from `[Database] backend` in
api_config.ini. Missing/empty setting defaults to postgres (the only backend
since the Firestore decommission); an unknown value fails loud at startup
instead of silently running the wrong store."""
from data.PostgresRepository import PostgresRepository
from data.Repository import Repository

from Utils.ApiConfig import ApiConfig

POSTGRES = 'postgres'


def create_repository(api_config: ApiConfig) -> Repository:
    # Normalized: the value is hand-edited on the server, and a stray capital
    # would otherwise crashloop the container instead of starting.
    backend = api_config.get_key('Database', 'backend', default='').strip().lower() or POSTGRES
    if backend == POSTGRES:
        return PostgresRepository(api_config)
    raise ValueError(f'Unknown [Database] backend "{backend}" - use "{POSTGRES}"')
