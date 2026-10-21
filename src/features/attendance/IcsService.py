import os.path
from datetime import timedelta
from ics import Calendar, Event, alarm

from data.DataAccess import DataAccess

from Enums.Event import Event as Ev

from domain.calendar.CalendarFeed import EVENT_DURATION
from domain.calendar.EventSummary import event_summary
from domain.calendar.Ics import event_uid

from Utils import PathUtils


def init_directory():
    ics_directory = PathUtils.get_ics_files_path()
    if not os.path.exists(ics_directory):
        os.mkdir(ics_directory)


class IcsService(object):
    def __init__(self, data_access: DataAccess, team_service):
        self.data_access = data_access
        self.team_service = team_service
        init_directory()

    def get_ics(self, event_type: Ev, doc_id: str):

        event = self.data_access.get_event(event_type, doc_id)
        name = event_summary(event_type, event, self.team_service.current_team().name)

        ics_event = Event(uid=event_uid(doc_id), name=name, begin=event.timestamp, duration=EVENT_DURATION,
                          location=event.location, alarms=[alarm.DisplayAlarm(trigger=timedelta(hours=-24))])

        filename = f'{event_type.name.lower()}-{doc_id}.ics'
        ics_file_path = os.path.join(PathUtils.get_ics_files_path(), filename)
        cal = Calendar()
        cal.events.add(ics_event)
        with open(ics_file_path, mode="w+") as ics_file:
            ics_file.writelines(cal.serialize_iter())

        return ics_file_path
