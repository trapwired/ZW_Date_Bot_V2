"""Inline language picker (/language). Dedicated callback channel like the admin
(AP#...) menu; NodeHandler routes on PREFIX.

Deliberately UNSTAMPED (no team stamp, like EV#/ONB#): the action only writes the
presser's own language preference, so a forwarded button can't damage another
team - and teamless users must be able to use it too.

Button labels are the languages' native names, identical in every UI language -
a user stuck in the wrong language must still recognize their own entry.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from localization.Languages import SUPPORTED_LANGUAGES, NATIVE_NAMES
from localization.Translator import t

PREFIX = 'LANG'
DELIMITER = '#'

PICKER = 'P'  # show the picker (the entry button on member menus); a language code sets it


def encode(action: str) -> str:
    return DELIMITER.join([PREFIX, action])


def is_language_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> str | None:
    """The action part (PICKER or a language code); the node validates codes."""
    if not is_language_callback(data):
        return None
    return data.split(DELIMITER)[1]


def build_entry_row() -> list[InlineKeyboardButton]:
    """The one row any member menu can append to offer the language picker."""
    return [InlineKeyboardButton(t('🗣 Language'), callback_data=encode(PICKER))]


def build_picker_markup(current_language: str | None) -> InlineKeyboardMarkup:
    rows = []
    for language in SUPPORTED_LANGUAGES:
        marker = '✅ ' if language == current_language else ''
        rows.append([InlineKeyboardButton(marker + NATIVE_NAMES[language], callback_data=encode(language))])
    return InlineKeyboardMarkup(rows)
