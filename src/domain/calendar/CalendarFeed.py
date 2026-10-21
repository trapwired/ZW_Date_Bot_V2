"""Which events a member's calendar feed shows and how each one is marked (plan §6).
Visibility and the right to answer follow the role here, not at the call site, so no
second reader can leak a spectator's timekeeping. Callers pass the season window."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from Enums import Audience
from Enums.AttendanceState import AttendanceState
from Enums.Event import Event
from Enums.Role import Role

from domain.EventVisibility import visible_event_types
from domain.calendar.EventSummary import event_summary
from domain.calendar.Ics import event_uid
from domain.entities.Attendance import Attendance

from Utils import PrintUtils

from localization.Translator import t

EVENT_DURATION = timedelta(minutes=90)

STATUS_CONFIRMED = 'CONFIRMED'
STATUS_TENTATIVE = 'TENTATIVE'

ANSWERED_YES_PREFIX = '✅ '
NOT_ANSWERED_YES_PREFIX = '❓ '


@dataclass(frozen=True)
class FeedEntry:
    uid: str
    start: datetime
    end: datetime
    summary: str
    status: str
    location: str | None
    description: str | None


def build_feed_entries(events_by_type: dict[Event, list], attendances: dict[str, Attendance],
                       role: Role, team_name: str) -> list[FeedEntry]:
    can_answer = role in Audience.PLAYERS.roles
    entries = []
    for event_type in visible_event_types(role):
        for event in events_by_type.get(event_type, []):
            summary = event_summary(event_type, event, team_name)
            if not can_answer:
                entries.append(_entry(event, summary, STATUS_CONFIRMED, description=None))
                continue
            state = _own_state(event, attendances)
            if state is AttendanceState.NO:
                continue
            answered_yes = state is AttendanceState.YES
            prefix = ANSWERED_YES_PREFIX if answered_yes else NOT_ANSWERED_YES_PREFIX
            status = STATUS_CONFIRMED if answered_yes else STATUS_TENTATIVE
            description = t('Your answer: {answer}', answer=PrintUtils.pretty_print_attendance(state))
            entries.append(_entry(event, prefix + summary, status, description))
    return sorted(entries, key=lambda entry: (entry.start, entry.uid))


def _own_state(event, attendances: dict[str, Attendance]) -> AttendanceState:
    # No attendance row means not answered yet, which the bot treats as UNSURE.
    attendance = attendances.get(event.doc_id)
    return attendance.state if attendance is not None else AttendanceState.UNSURE


def _entry(event, summary: str, status: str, description: str | None) -> FeedEntry:
    return FeedEntry(uid=event_uid(event.doc_id),
                     start=event.timestamp,
                     end=event.timestamp + EVENT_DURATION,
                     summary=summary,
                     status=status,
                     location=event.location or None,
                     description=description)
