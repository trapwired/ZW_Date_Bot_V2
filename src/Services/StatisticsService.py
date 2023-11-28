from Data import DataAccess

from Enums.Event import Event

from databaseEntities.TelegramUser import TelegramUser


class StatisticsService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def increment_event_reminder_metric(self, event_type: Event, player: TelegramUser, num_events: int):
        # data_access - increment metric on player
        reminder_metric = self.data_access.get_player_metric(player.telegramId)
        reminder_metric.update_event_reminders(event_type, num_events)
        self.data_access.update(reminder_metric)
