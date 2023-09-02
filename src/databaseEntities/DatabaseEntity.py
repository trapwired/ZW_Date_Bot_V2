from abc import ABC


class DatabaseEntity(ABC):
    def __init__(self, doc_id: str | None):
        self.doc_id = doc_id

    def add_document_id(self, doc_id: str):
        self.doc_id = doc_id
        return self
