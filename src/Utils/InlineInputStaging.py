"""Codec for typed input staged in a user state's ``additional_info``.

An admin who presses an inline button then types a value (a website URL, a
spectator password, ...) has nowhere to keep that value: it doesn't fit in
callback_data, and it must survive until they press Save. We stage it alongside
the ids of the menu message to keep re-rendering, encoded as
``message_id#chat_id#value``. Shared by every typed-input admin slice so the
encoding can't drift between them.
"""

_DELIMITER = '#'


def build(message_id: int | None, chat_id: int | None, value: str) -> str:
    return _DELIMITER.join([str(message_id or ''), str(chat_id or ''), value])


def parse(staged: str) -> tuple[int | None, int | None, str]:
    """-> (menu message_id, chat_id, value). Values may contain '#' (e.g. a URL),
    so only the two leading id fields are split off; a legacy plain-value string
    parses as id-less."""
    parts = staged.split(_DELIMITER, 2)
    if len(parts) != 3:
        return None, None, staged
    message_id, chat_id, value = parts
    try:
        return int(message_id), int(chat_id), value
    except ValueError:
        return None, None, value
