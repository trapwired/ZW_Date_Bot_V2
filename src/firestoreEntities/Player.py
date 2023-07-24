from src.States.PlayerState import PlayerState


class Player:
    def __init__(self, telegram_id: int, firstname: str, lastname: str):
        self.lastname = lastname
        self.firstname = firstname
        self.telegramId = telegram_id

    @staticmethod
    def from_dict(source: dict):
        return Player(source['telegramId'], source['firstname'], source['lastname'])

    def to_dict(self):
        return {'telegramId': self.telegramId,
                'firstname': self.firstname,
                'lastname': self.lastname}

    def __repr__(self):
        return f"Player(telegramId={self.telegramId}, firstname={self.firstname}, lastname={self.lastname})"
