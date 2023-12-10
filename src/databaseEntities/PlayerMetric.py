from databaseEntities.DatabaseEntity import DatabaseEntity

from Enums.Event import Event


class PlayerMetric(DatabaseEntity):
    def __init__(self, user_id: str, game_reminders_sent: int, training_reminders_sent: int,
                 timekeeping_reminders_sent: int, doc_id: str = None):
        super().__init__(doc_id)
        self.user_id = user_id
        self.game_reminders_sent = int(game_reminders_sent)
        self.training_reminders_sent = int(training_reminders_sent)
        self.timekeeping_reminders_sent = int(timekeeping_reminders_sent)

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return PlayerMetric(source['userId'], source['gameRemindersSent'], source['trainingRemindersSent'],
                            source['timekeepingRemindersSent'], doc_id)

    def to_dict(self):
        return {'userId': self.user_id,
                'gameRemindersSent': self.game_reminders_sent,
                'trainingRemindersSent': self.training_reminders_sent,
                'timekeepingRemindersSent': self.timekeeping_reminders_sent}

    def update_event_reminders(self, event_type: Event, num_events: int):
        match event_type:
            case Event.GAME:
                self.game_reminders_sent += num_events
            case Event.TRAINING:
                self.training_reminders_sent += num_events
            case Event.TIMEKEEPING:
                self.timekeeping_reminders_sent += num_events

    def sum_values(self):
        return self.timekeeping_reminders_sent + self.training_reminders_sent + self.game_reminders_sent

    def __repr__(self):
        return (f"PlayerMetric(userId={self.user_id}, gameRemindersSent={self.game_reminders_sent}, "
                f"trainingRemindersSent={self.training_reminders_sent}, timekeepingRemind"
                f"ersSent={self.timekeeping_reminders_sent}, doc_id={self.doc_id})")
