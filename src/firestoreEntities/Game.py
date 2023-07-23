import datetime


class Game:

    def __init__(self, timestamp: datetime, location: str, opponent: str):
        self.timestamp = timestamp
        self.location = location
        self.opponent = opponent

    @staticmethod
    def from_dict(source):
        return Game(source['timestamp'], source['location'], source['opponent'])

    def to_dict(self):
        return {'timestamp': self.timestamp,
                'location': self.location,
                'opponent': self.opponent}

    def __repr__(self):
        return f"Game(timestamp={self.timestamp}, location={self.location}, opponent={self.opponent})"
