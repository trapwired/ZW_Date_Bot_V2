from Enums.Event import Event

from domain.entities.DatabaseEntity import DatabaseEntity


class Team(DatabaseEntity):

    def __init__(self, name: str, group_chat_id: int, spectator_password: str = None,
                 trainers_games: list[int] = None, trainers_training: list[int] = None, doc_id: str = None):
        super().__init__(doc_id)
        self.name = name
        self.group_chat_id = int(group_chat_id)
        self.spectator_password = spectator_password
        self.trainers_games = trainers_games if trainers_games is not None else []
        self.trainers_training = trainers_training if trainers_training is not None else []

    def trainer_chat_ids(self, event_type: Event) -> list[int]:
        """Where this team's trainer-facing messages (summaries, trigger warnings) go.
        A team with no trainers configured falls back to its group chat - always
        sendable, so a freshly registered team never loses messages."""
        match event_type:
            case Event.TRAINING:
                trainers = self.trainers_training
            case Event.GAME | Event.TIMEKEEPING:
                trainers = self.trainers_games
            case _:
                raise ValueError(f'Unhandled event type: {event_type}')
        return trainers or [self.group_chat_id]

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Team(source.get('name'), source.get('groupChatId'), source.get('spectatorPassword'),
                    source.get('trainersGames', []), source.get('trainersTraining', []), doc_id)

    def to_dict(self):
        return {'name': self.name,
                'groupChatId': self.group_chat_id,
                'spectatorPassword': self.spectator_password,
                'trainersGames': self.trainers_games,
                'trainersTraining': self.trainers_training}

    def __repr__(self):
        return f"Team(name={self.name}, group_chat_id={self.group_chat_id}, spectator_password={self.spectator_password}, trainers_games={self.trainers_games}, trainers_training={self.trainers_training}, doc_id={self.doc_id})"
