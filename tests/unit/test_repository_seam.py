"""The storage seam (Stage B): backend choice is config, defaults keep existing
deployments on Firestore, and the interface cannot silently drift behind the
Firestore implementation (a method added there but not on Repository would never
be enforced on the Postgres backend)."""
import configparser

import pytest

from data import RepositoryFactory
from data.FirebaseRepository import FirebaseRepository
from data.Repository import Repository


class FakeApiConfig:
    def __init__(self, backend: str | None):
        self.backend = backend

    def get_key(self, section: str, identifier: str):
        if self.backend is None:
            raise configparser.NoSectionError(section)
        return self.backend


def test_missing_database_section_defaults_to_firestore():
    assert RepositoryFactory._configured_backend(FakeApiConfig(None)) == RepositoryFactory.FIRESTORE


def test_postgres_backend_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        RepositoryFactory.create_repository(FakeApiConfig('postgres'))


def test_unknown_backend_fails_loud():
    with pytest.raises(ValueError, match='mongodb'):
        RepositoryFactory.create_repository(FakeApiConfig('mongodb'))


def test_firebase_repository_has_no_public_method_outside_the_interface():
    interface = {m for m in dir(Repository) if not m.startswith('_')}
    implementation = {name for name, member in vars(FirebaseRepository).items()
                      if not name.startswith('_') and callable(member)}
    outside = implementation - interface
    assert not outside, f'Add to Repository (or make private): {sorted(outside)}'
