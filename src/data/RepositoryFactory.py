"""Resolves which storage backend runs, from `[Database] backend` in
api_config.ini. Missing/empty setting defaults to firestore so existing deployed
configs keep working untouched; an unknown value fails loud at startup instead
of silently running the wrong store."""
from data.FirebaseRepository import FirebaseRepository
from data.PostgresRepository import PostgresRepository
from data.Repository import Repository
from data.Tables import Tables

from Utils.ApiConfig import ApiConfig

FIRESTORE = 'firestore'
POSTGRES = 'postgres'


def create_repository(api_config: ApiConfig) -> Repository:
    # Normalized: the value is hand-edited on the server at cutover, and a stray
    # capital would otherwise crashloop the container instead of starting.
    backend = api_config.get_key('Database', 'backend', default='').strip().lower() or FIRESTORE
    if backend == FIRESTORE:
        return FirebaseRepository(api_config, Tables(api_config))
    if backend == POSTGRES:
        return PostgresRepository(api_config)
    raise ValueError(f'Unknown [Database] backend "{backend}" - use "{FIRESTORE}" or "{POSTGRES}"')
