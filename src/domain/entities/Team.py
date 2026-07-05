from Enums.Event import Event

from domain.entities.DatabaseEntity import DatabaseEntity


class Team(DatabaseEntity):

    def __init__(self, name: str, group_chat_id: int, spectator_password: str = None,
                 trainers_games: list[int] = None, trainers_training: list[int] = None,
                 invite_tokens: list[str] = None, doc_id: str = None):
        super().__init__(doc_id)
        self.name = name
        self.group_chat_id = int(group_chat_id)
        self.spectator_password = spectator_password
        self.trainers_games = self._clean_trainer_ids(trainers_games)
        self.trainers_training = self._clean_trainer_ids(trainers_training)
        # Outstanding one-time spectator invites; a token is deleted when redeemed.
        self.invite_tokens = list(invite_tokens) if invite_tokens is not None else []

    def trainer_chat_ids(self, event_type: Event) -> list[int]:
        """Where this team's trainer-facing messages (summaries, trigger warnings) go.
        A team with no trainers configured falls back to its group chat - always
        sendable, so a freshly registered team never loses messages."""
        return self.trainers_for(event_type) or [self.group_chat_id]

    def toggle_trainer(self, event_type: Event, chat_id: int) -> None:
        """Add chat_id to (or remove it from) the trainer list for this event group.
        Persist through TeamService.toggle_trainer, which owns the write."""
        trainers = self.trainers_for(event_type)
        if chat_id in trainers:
            trainers.remove(chat_id)
        else:
            trainers.append(chat_id)

    @staticmethod
    def _clean_trainer_ids(chat_ids: list | None) -> list[int]:
        # Copy + int-coerce + dedupe (order-preserving): the entity owns its lists
        # (callers and test doubles must not share mutable state with it), and
        # hand-edited docs may hold string ids or duplicates - toggle/removal
        # matching needs clean ints.
        if chat_ids is None:
            return []
        return list(dict.fromkeys(int(chat_id) for chat_id in chat_ids))

    def trainers_for(self, event_type: Event) -> list[int]:
        """THE event-group-to-trainer-list mapping - render, toggle and routing all
        resolve through here so they cannot drift apart."""
        match event_type:
            case Event.TRAINING:
                return self.trainers_training
            case Event.GAME | Event.TIMEKEEPING:
                return self.trainers_games
            case _:
                raise ValueError(f'Unhandled event type: {event_type}')

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return Team(source.get('name'), source.get('groupChatId'), source.get('spectatorPassword'),
                    source.get('trainersGames', []), source.get('trainersTraining', []),
                    source.get('inviteTokens', []), doc_id)

    def to_dict(self):
        return {'name': self.name,
                'groupChatId': self.group_chat_id,
                'spectatorPassword': self.spectator_password,
                'trainersGames': list(self.trainers_games),
                'trainersTraining': list(self.trainers_training),
                'inviteTokens': list(self.invite_tokens)}

    def __repr__(self):
        return f"Team(name={self.name}, group_chat_id={self.group_chat_id}, spectator_password={self.spectator_password}, trainers_games={self.trainers_games}, trainers_training={self.trainers_training}, doc_id={self.doc_id})"
