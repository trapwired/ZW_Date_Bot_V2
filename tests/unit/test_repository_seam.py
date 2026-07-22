"""The storage seam: backend choice is config, a missing setting defaults to
postgres (the only backend since the Firestore decommission), hand-edit typos
don't crashloop the bot, and no backend can silently grow public surface behind
the Repository interface (a method added on one backend but not on Repository
would never be enforced on the other)."""
import pytest

from data import RepositoryFactory
from data.PostgresRepository import PostgresRepository
from data.Repository import Repository

from tests.doubles.in_memory_repository import InMemoryRepository


class FakeApiConfig:
    """Only get_key matters here; None models a missing section/key."""

    def __init__(self, backend: str | None):
        self.backend = backend

    def get_key(self, section: str, identifier: str, default=None):
        return default if self.backend is None else self.backend


@pytest.mark.parametrize('configured', [None, '', '  ', 'postgres', 'Postgres', ' POSTGRES '])
def test_backend_resolves_to_postgres(monkeypatch, configured):
    # Constructing the real PostgresRepository would need a reachable server; the
    # factory's job is the choice, so the construction itself is stubbed out.
    # Case/whitespace are normalized: a hand-edited config must reach the intended
    # branch, not the unknown-backend error (which would crashloop the container).
    monkeypatch.setattr(RepositoryFactory, 'PostgresRepository', lambda *a, **k: 'postgres-repo')
    assert RepositoryFactory.create_repository(FakeApiConfig(configured)) == 'postgres-repo'


def test_unknown_backend_fails_loud():
    with pytest.raises(ValueError, match='mongodb'):
        RepositoryFactory.create_repository(FakeApiConfig('mongodb'))


@pytest.mark.parametrize('backend', [InMemoryRepository, PostgresRepository])
def test_backends_expose_nothing_outside_the_interface(backend):
    interface = {m for m in dir(Repository) if not m.startswith('_')}
    # Constants (e.g. SETTINGS_DOC_ID) are implementation detail; every public member
    # that carries behaviour - methods AND properties - must be declared.
    implementation = {name for name, member in vars(backend).items()
                      if not name.startswith('_') and (callable(member) or isinstance(member, property))}

    assert not implementation - interface, \
        f'Add to Repository (or make private): {sorted(implementation - interface)}'
