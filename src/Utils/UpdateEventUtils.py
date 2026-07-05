from Enums.EventField import EventField
from Enums.Event import Event

from Utils import PrintUtils

from localization.Translator import t


def get_input_format_string(field: EventField):
    match field:
        case EventField.OPPONENT:
            return t('freetext, spaces allowed, no max length, but end will be trimmed')
        case EventField.LOCATION:
            return t('freetext, spaces allowed, no max length, but end will be trimmed')
        case EventField.DATETIME:
            return t('numbers and symbols, format: {example}', example='20.03.2023 19:38')


def get_inline_message(prefix_string: str, event_type: Event, event_summary: str) -> str:
    return f'{prefix_string} {PrintUtils.event_label(event_type)}: {event_summary}'
