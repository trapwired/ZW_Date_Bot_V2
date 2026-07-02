from typing import NamedTuple

from Enums.Event import Event
from Enums.EventField import EventField

DELIMITER = '#'


class EventFieldEdit(NamedTuple):
    """The context for a single-field event edit, stashed in UsersToState.additional_info
    while the admin types the new value (the inline message to update, plus which event
    and field are being edited)."""
    message_id: int
    chat_id: int
    doc_id: str
    event_type: Event
    field: EventField


def build_additional_information(message_id: int, chat_id: int, event_document_id: str, event_type: Event,
                                 field: EventField) -> str:
    return DELIMITER.join([str(message_id), str(chat_id), event_document_id, str(int(event_type)), str(int(field))])


def try_parse_additional_information(message: str) -> EventFieldEdit | None:
    split = message.split(DELIMITER)
    if len(split) != 5:
        return None

    try:
        return EventFieldEdit(int(split[0]), int(split[1]), split[2], Event(int(split[3])),
                              EventField(int(split[4])))
    except ValueError:
        return None
