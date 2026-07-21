"""Resolves which storage backend runs, from `[Database] backend` in
api_config.ini. Missing section/key defaults to firestore so existing deployed
configs keep working untouched; an unknown value fails loud at startup instead
of silently running the wrong store."""
import configparser

from data.FirebaseRepository import FirebaseRepository
from data.Repository import Repository
from data.Tables import Tables

from Utils.ApiConfig import ApiConfig

FIRESTORE = 'firestore'
POSTGRES = 'postgres'


def create_repository(api_config: ApiConfig) -> Repository:
    match _configured_backend(api_config):
        case x if x == FIRESTORE:
            return FirebaseRepository(api_config, Tables(api_config))
        case x if x == POSTGRES:
            raise NotImplementedError('postgres backend lands in Stage B2 of the VPS migration')
        case unknown:
            raise ValueError(f'Unknown [Database] backend "{unknown}" - use "{FIRESTORE}" or "{POSTGRES}"')


def _configured_backend(api_config: ApiConfig) -> str:
    try:
        return api_config.get_key('Database', 'backend')
    except (configparser.NoSectionError, configparser.NoOptionError):
        return FIRESTORE
