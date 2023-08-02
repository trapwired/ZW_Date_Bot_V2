class Player:
    def __init__(self, telegram_id: int, firstname: str, lastname: str, doc_id: str = None):
        self.doc_id = doc_id
        self.lastname = lastname
        self.firstname = firstname
        self.telegramId = telegram_id

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Player(source['telegramId'], source['firstname'], source['lastname'], doc_id)

    def to_dict(self):
        return {'telegramId': self.telegramId,
                'firstname': self.firstname,
                'lastname': self.lastname}

    def __repr__(self):
        return f"Player(telegramId={self.telegramId}, firstname={self.firstname}, lastname={self.lastname}, doc_id={self.doc_id})"
