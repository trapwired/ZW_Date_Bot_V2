from domain.entities.DatabaseEntity import DatabaseEntity


class Settings(DatabaseEntity):
    def __init__(self, website: str, doc_id: str = None):
        super().__init__(doc_id)
        self.website = website

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Settings(source['website'], doc_id)

    def to_dict(self):
        return {'website': self.website}

    def __repr__(self):
        return f"Settings(website={self.website}, doc_id={self.doc_id})"
