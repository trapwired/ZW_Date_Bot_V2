import os.path
from datetime import timedelta
from ics import Calendar, Event, alarm

from Data import DataAccess

from Enums.Event import Event as Ev

from Utils import PathUtils


def init_directory():
    ics_directory = PathUtils.get_ics_files_path()
    if not os.path.exists(ics_directory):
        os.mkdir(ics_directory)


class IcsService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access
        init_directory()

        self.DURATION_GAME = timedelta(minutes=90)
        self.DURATION_TRAINING = timedelta(minutes=90)
        self.DURATION_TIMEKEEPING = timedelta(minutes=90)

    def get_ics(self, event_type: Ev, doc_id: str):

        event = self.data_access.get_event(event_type, doc_id)
        event_title = event_type.name.lower()

        name = f'Handball {event_title.capitalize()} Züri West'
        begin = event.timestamp

        match event_type:
            case Ev.GAME:
                name += f' ({event.opponent})'
                duration = self.DURATION_GAME
            case Ev.TRAINING:
                duration = self.DURATION_TRAINING
            case Ev.TIMEKEEPING:
                duration = self.DURATION_TIMEKEEPING
            case _:
                raise TypeError('Event type not known')

        location = event.location

        event = Event(name=name, begin=begin, duration=duration, location=location,
                      alarms=[alarm.DisplayAlarm(trigger=timedelta(hours=-24))])

        filename = f'{event_title}-{doc_id}.ics'
        ics_file_path = os.path.join(PathUtils.get_ics_files_path(), filename)
        cal = Calendar()
        cal.events.add(event)
        with open(ics_file_path, mode="w+") as ics_file:
            ics_file.writelines(cal.serialize_iter())

        return ics_file_path
