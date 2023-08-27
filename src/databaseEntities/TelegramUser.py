class TelegramUser(object):
    def __init__(self, telegram_id: int, firstname: str, lastname: str, doc_id: str = None):
        self.doc_id = doc_id
        self.lastname = str(lastname or '')
        self.firstname = str(firstname or '')
        if type(telegram_id) is str:
            telegram_id = int(telegram_id)
        self.telegramId = telegram_id

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return TelegramUser(source['telegramId'], source['firstname'], source['lastname'], doc_id)

    def add_document_id(self, doc_id: str):
        self.doc_id = doc_id
        return self

    def to_dict(self):
        return {'telegramId': self.telegramId,
                'firstname': self.firstname,
                'lastname': self.lastname}

    def __repr__(self):
        return f"TelegramUser(telegramId={self.telegramId}, firstname={self.firstname}, lastname={self.lastname}, doc_id={self.doc_id})"
