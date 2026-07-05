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

PREFIX = 'LANG'
DELIMITER = '#'


def encode(language: str) -> str:
    return DELIMITER.join([PREFIX, language])


def is_language_callback(data: str) -> bool:
    return data.startswith(PREFIX + DELIMITER)


def parse(data: str) -> str | None:
    if not is_language_callback(data):
        return None
    language = data.split(DELIMITER)[1]
    return language if language in SUPPORTED_LANGUAGES else None


def build_picker_markup(current_language: str | None) -> InlineKeyboardMarkup:
    rows = []
    for language in SUPPORTED_LANGUAGES:
        marker = '✅ ' if language == current_language else ''
        rows.append([InlineKeyboardButton(marker + NATIVE_NAMES[language], callback_data=encode(language))])
    return InlineKeyboardMarkup(rows)
