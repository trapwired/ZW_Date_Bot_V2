"""Inline buttons of the calendar subscription. Own callback channel (CAL#...) like the
language picker (LANG#...); NodeHandler routes on PREFIX.

Deliberately UNSTAMPED (no team stamp): both actions only touch the presser's own
link, so a forwarded button can't affect anyone else."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from localization.Translator import t

PREFIX = 'CAL'
DELIMITER = '#'

SHOW = 'S'    # first tap issues a link, later taps show its status
ROTATE = 'R'  # replace the link; the old one stops working at once

ACTIONS = (SHOW, ROTATE)


def encode(action: str) -> str:
    return DELIMITER.join([PREFIX, action])


def is_calendar_feed_callback(callback_data: str) -> bool:
    return callback_data.startswith(PREFIX + DELIMITER)


def decode(callback_data: str) -> str | None:
    if not is_calendar_feed_callback(callback_data):
        return None
    action = callback_data[len(PREFIX + DELIMITER):]
    return action if action in ACTIONS else None


def build_entry_row() -> list[InlineKeyboardButton]:
    """The row the events list appends to offer the subscription."""
    return [InlineKeyboardButton(t('📆 Subscribe calendar'), callback_data=encode(SHOW))]


def build_link_markup(google_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t('Open in Google Calendar'), url=google_url)],
        _rotate_row(),
    ])


def build_rotate_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([_rotate_row()])


def _rotate_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(t('🔄 New link'), callback_data=encode(ROTATE))]
