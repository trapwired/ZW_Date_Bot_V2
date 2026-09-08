from domain.entities.DatabaseEntity import DatabaseEntity


class Settings(DatabaseEntity):
    def __init__(self, website: str, shv_team_id: int = None, doc_id: str = None):
        super().__init__(doc_id)
        self.website = website
        # SHV matchcenter team id for the schedule sync; None disables the sync.
        self.shv_team_id = int(shv_team_id) if shv_team_id is not None else None

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Settings(source['website'], source.get('shvTeamId'), doc_id)

    def to_dict(self):
        return {'website': self.website,
                'shvTeamId': self.shv_team_id}

    def __repr__(self):
        return f"Settings(website={self.website}, shv_team_id={self.shv_team_id}, doc_id={self.doc_id})"
