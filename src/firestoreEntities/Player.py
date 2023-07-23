class Player:
    def __init__(self, telegram_id, firstname, lastname, state):
        self.state = state
        self.lastname = lastname
        self.firstname = firstname
        self.telegramId = telegram_id

    @staticmethod
    def from_dict(source):
        return Player(source['telegramId'], source['firstname'], source['lastname'], source['state'])

    def to_dict(self):
        return {'telegramId': self.telegramId,
                'firstname': self.firstname,
                'lastname': self.lastname,
                'state': self.state}

    def __repr__(self):
        return f"Player(\
                telegramId={self.telegramId}, \
                firstname={self.firstname}, \
                lastname={self.lastname}, \
                state={self.state}\
            )"
