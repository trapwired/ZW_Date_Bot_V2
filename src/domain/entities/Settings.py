from domain.entities.DatabaseEntity import DatabaseEntity


class Settings(DatabaseEntity):
    def __init__(self, website: str, shv_sync_disabled: bool = False, doc_id: str = None):
        super().__init__(doc_id)
        self.website = website
        # Maintainer switch: the SHV schedule sync derives its team id from the
        # website and runs unless this is set.
        self.shv_sync_disabled = bool(shv_sync_disabled)

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Settings(source['website'], source.get('shvSyncDisabled') or False, doc_id)

    def to_dict(self):
        return {'website': self.website,
                'shvSyncDisabled': self.shv_sync_disabled}

    def __repr__(self):
        return f"Settings(website={self.website}, shv_sync_disabled={self.shv_sync_disabled}, doc_id={self.doc_id})"
