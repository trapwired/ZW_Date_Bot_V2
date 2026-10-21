"""THE calendar title of an event, shared by the per-event download and the
subscribed feed so both name the same event the same way."""
from Enums.Event import Event

from localization.Translator import t


def event_summary(event_type: Event, event, team_name: str) -> str:
    summary = t('Handball {type} {team}', type=t(event_type.name.title()), team=team_name)
    if event_type is Event.GAME:
        summary += f' ({event.opponent})'
    return summary
