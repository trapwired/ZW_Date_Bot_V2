from data.DataAccess import DataAccess

from Enums.Event import Event

from domain.entities.TelegramUser import TelegramUser


class StatisticsService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def increment_event_reminder_metric(self, event_type: Event, player: TelegramUser, num_events: int):
        # data_access - increment metric on player
        reminder_metric = self.data_access.get_player_metric(player.telegramId)
        reminder_metric.update_event_reminders(event_type, num_events)
        self.data_access.update(reminder_metric)

    def get_player_reminder_metrics(self) -> dict:
        return self.data_access.get_user_to_player_metric()

    def get_attendance_statistics(self, event_type: Event):
        return self.data_access.get_attendance_statistics(event_type)

    def get_event_attendance_summary(self, doc_id: str, event_type: Event):
        # get_stats_event + get_names always go together: the counts are useless to the
        # caller without the names, so resolve both here.
        stats = self.data_access.get_stats_event(doc_id, event_type)
        return self.data_access.get_names(stats)

    def reset_reminder_statistics(self) -> int:
        return self.data_access.reset_statistics()
