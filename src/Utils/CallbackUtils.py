from typing import NamedTuple

from Enums.Event import Event
from Enums.EventField import EventField

DELIMITER = '#'


class EventFieldEdit(NamedTuple):
    """The context for a single-field event edit, stashed in UsersToState.additional_info
    while the admin types the new value (the event-card message to refresh, which event
    and field are being edited, and the prompt message to clean up afterwards)."""
    message_id: int
    chat_id: int
    doc_id: str
    event_type: Event
    field: EventField
    prompt_message_id: int | None = None


def build_additional_information(message_id: int, chat_id: int, event_document_id: str, event_type: Event,
                                 field: EventField, prompt_message_id: int | None = None) -> str:
    parts = [str(message_id), str(chat_id), event_document_id, str(int(event_type)), str(int(field))]
    if prompt_message_id is not None:
        parts.append(str(prompt_message_id))
    return DELIMITER.join(parts)


def try_parse_additional_information(message: str) -> EventFieldEdit | None:
    split = message.split(DELIMITER)
    # The prompt id was added later; contexts stashed before that have 5 fields.
    if len(split) not in (5, 6):
        return None

    try:
        prompt_message_id = int(split[5]) if len(split) == 6 else None
        return EventFieldEdit(int(split[0]), int(split[1]), split[2], Event(int(split[3])),
                              EventField(int(split[4])), prompt_message_id)
    except ValueError:
        return None
