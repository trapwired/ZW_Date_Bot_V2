"""In-memory stand-in for the Firestore client (``self.db`` inside FirebaseRepository).

We double at the Firestore-client boundary so the real FirebaseRepository and
DataAccess run unchanged on top of it — that keeps both under test during the
refactor. Only the client surface actually exercised by FirebaseRepository is
implemented; anything else raises so gaps surface loudly instead of silently.
"""
from datetime import datetime

import pandas as pd


def _strip_tz(value):
    # Stored event timestamps are tz-aware (Europe/Zurich); query bounds are naive
    # datetimes. Normalise both to naive for ordering comparisons, mirroring how
    # Firestore compares instants regardless of the client's tz representation.
    if isinstance(value, pd.Timestamp):
        return value.tz_localize(None) if value.tzinfo is not None else value
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


class FakeFieldFilter:
    """Replaces google FieldFilter inside FirebaseRepository during tests."""

    def __init__(self, field, op, value):
        self.field = field
        self.op = op
        self.value = value

    def matches(self, data: dict) -> bool:
        actual = data.get(self.field)
        if self.op == "==":
            return actual == self.value
        if self.op == "in":
            return actual in self.value
        if self.op in (">", "<", ">=", "<="):
            if actual is None:
                return False
            a, b = _strip_tz(actual), _strip_tz(self.value)
            if self.op == ">":
                return a > b
            if self.op == "<":
                return a < b
            if self.op == ">=":
                return a >= b
            return a <= b
        raise NotImplementedError(f"FakeFieldFilter op not supported: {self.op}")


class FakeSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class FakeDocumentRef:
    def __init__(self, collection: "FakeCollection", doc_id: str):
        self._collection = collection
        self.id = doc_id

    def get(self):
        return FakeSnapshot(self.id, self._collection.store.get(self.id))

    def set(self, data: dict):
        self._collection.store[self.id] = dict(data)

    def update(self, data: dict):
        # Firestore update() merges top-level keys, it does not replace the doc.
        existing = self._collection.store.setdefault(self.id, {})
        existing.update(data)

    def delete(self):
        self._collection.store.pop(self.id, None)

    def collection(self, name: str) -> "FakeCollection":
        # Subcollections key the shared storage by path, mirroring Firestore's hierarchy.
        # Works even for a doc that doesn't exist yet - Firestore allows that too.
        return FakeCollection(self._collection._client, f"{self._collection.name}/{self.id}/{name}")


class FakeQuery:
    def __init__(self, collection: "FakeCollection", filters):
        self._collection = collection
        self._filters = filters

    def where(self, filter=None):  # noqa: A002 - mirrors Firestore kwarg name
        return FakeQuery(self._collection, self._filters + [filter])

    def _matching(self):
        for doc_id, data in list(self._collection.store.items()):
            if all(f.matches(data) for f in self._filters):
                yield FakeSnapshot(doc_id, data)

    def get(self):
        return list(self._matching())

    def stream(self):
        return iter(self.get())


class FakeCollection:
    def __init__(self, client: "FakeFirestoreClient", name: str):
        self._client = client
        self.name = name
        self.store = client.storage.setdefault(name, {})

    def document(self, doc_id: str = None):
        if doc_id is None:
            doc_id = self._client.next_id()
        return FakeDocumentRef(self, doc_id)

    def where(self, filter=None):  # noqa: A002 - mirrors Firestore kwarg name
        return FakeQuery(self, [filter])

    def add(self, data: dict):
        doc_id = self._client.next_id()
        self.store[doc_id] = dict(data)
        # Firestore returns (update_time, DocumentReference); callers read doc_ref[1].id.
        return (None, FakeDocumentRef(self, doc_id))

    def stream(self):
        return iter([FakeSnapshot(doc_id, data) for doc_id, data in list(self.store.items())])

    def get(self):
        return list(self.stream())


class FakeFirestoreClient:
    def __init__(self):
        self.storage = {}
        self._counter = 0

    def next_id(self) -> str:
        self._counter += 1
        return f"doc{self._counter}"

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self, name)
