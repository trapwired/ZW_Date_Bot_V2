"""Inline yes/no buttons for the SHV sync's admin questions. Dedicated callback
channel (SHV#...) like the admin menu; NodeHandler routes on PREFIX.

The payload is the decision's short token, not its row id: uuid ids plus the team
stamp would blow Telegram's 64-byte callback_data budget (the PR #70 lesson).
STAMPED like the other admin channels - a forwarded button pressed by another
team's admin must not act on the presser's team.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from framework import TeamStamp

from localization.Translator import t

PREFIX = 'SHV'
DELIMITER = '#'

YES = 'Y'
NO = 'N'

# Maintainer-only action; a decision token (11 chars, token_urlsafe) can never be 'M'.
MAINTAINER_DISABLE = 'M'


def encode(token: str, answer: str) -> str:
    return TeamStamp.stamp(DELIMITER.join([PREFIX, token, answer]))


def encode_maintainer_disable(team_id: str) -> str:
    # Deliberately UNSTAMPED: the maintainer presses this outside the affected team's
    # context, and the payload itself names the team to act on. The callback node
    # gates it on the maintainer chat id instead.
    return DELIMITER.join([PREFIX, MAINTAINER_DISABLE, team_id])


def is_shv_sync_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> tuple[str, str] | None:
    """(token, answer), or None for a malformed or maintainer payload."""
    parts = TeamStamp.strip(data).split(DELIMITER)
    if len(parts) != 3 or parts[2] not in (YES, NO):
        return None
    return parts[1], parts[2]


def parse_maintainer_disable(data: str) -> str | None:
    """The team id of a maintainer-disable press, or None for any other payload."""
    parts = data.split(DELIMITER)
    if len(parts) != 3 or parts[1] != MAINTAINER_DISABLE:
        return None
    return parts[2]


def build_question_markup(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t('✅ Yes'), callback_data=encode(token, YES)),
        InlineKeyboardButton(t('❌ No'), callback_data=encode(token, NO)),
    ]])


def build_maintainer_disable_markup(team_id: str) -> InlineKeyboardMarkup:
    # Maintainer-facing, like every maintainer diagnostic: English, no t().
    return InlineKeyboardMarkup([[
        InlineKeyboardButton('🚫 Disable SHV sync for this team',
                             callback_data=encode_maintainer_disable(team_id)),
    ]])
