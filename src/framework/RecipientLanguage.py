"""Per-recipient language for fan-out sends (reminders, event pushes,
announcements, role notices): the recipient's stored language, else English.

A recipient's Telegram client language is only visible during their OWN updates,
so NodeHandler snapshots it into the profile on first contact - by the time a
fan-out runs, the stored value is all there is.
"""
from contextlib import contextmanager

from localization.LanguageContext import language_context
from localization.Languages import resolve_user_language

from Utils.CustomExceptions import ObjectNotFoundException


@contextmanager
def recipient_language_context(data_access, telegram_id: int):
    try:
        saved = data_access.get_user_state(telegram_id).language
    except ObjectNotFoundException:
        saved = None
    with language_context(resolve_user_language(saved, None)):
        yield
