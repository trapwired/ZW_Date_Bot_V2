"""The storage seam (Stage B): backend choice is config, defaults keep existing
deployments on Firestore, hand-edit typos don't crashloop the bot, and the
interface cannot silently drift behind the Firestore implementation (a method
added there but not on Repository would never be enforced on the Postgres
backend)."""
import pytest

from data import RepositoryFactory
from data.FirebaseRepository import FirebaseRepository
from data.Repository import Repository


class FakeApiConfig:
    """Only get_key matters here; None models a missing section/key."""

    def __init__(self, backend: str | None):
        self.backend = backend

    def get_key(self, section: str, identifier: str, default=None):
        return default if self.backend is None else self.backend


@pytest.mark.parametrize('configured', [None, '', '  '])
def test_unset_backend_defaults_to_firestore(monkeypatch, configured):
    # Constructing the real FirebaseRepository would need credentials; the factory's
    # job is the choice, so the construction itself is stubbed out.
    monkeypatch.setattr(RepositoryFactory, 'FirebaseRepository', lambda *a, **k: 'firestore-repo')
    monkeypatch.setattr(RepositoryFactory, 'Tables', lambda *a, **k: None)

    assert RepositoryFactory.create_repository(FakeApiConfig(configured)) == 'firestore-repo'


@pytest.mark.parametrize('configured', ['postgres', 'Postgres', ' POSTGRES '])
def test_postgres_backend_normalized(monkeypatch, configured):
    # Case/whitespace are normalized: a hand-edited config at cutover must reach the
    # intended branch, not the unknown-backend error (which would crashloop the container).
    monkeypatch.setattr(RepositoryFactory, 'PostgresRepository', lambda *a, **k: 'postgres-repo')
    assert RepositoryFactory.create_repository(FakeApiConfig(configured)) == 'postgres-repo'


def test_unknown_backend_fails_loud():
    with pytest.raises(ValueError, match='mongodb'):
        RepositoryFactory.create_repository(FakeApiConfig('mongodb'))


def test_firebase_repository_exposes_nothing_outside_the_interface():
    interface = {m for m in dir(Repository) if not m.startswith('_')}
    # Constants (SETTINGS_DOC_ID, FIRESTORE_IN_LIMIT) are implementation detail; every
    # public member that carries behaviour - methods AND properties - must be declared.
    implementation = {name for name, member in vars(FirebaseRepository).items()
                      if not name.startswith('_') and (callable(member) or isinstance(member, property))}

    assert not implementation - interface, \
        f'Add to Repository (or make private): {sorted(implementation - interface)}'
