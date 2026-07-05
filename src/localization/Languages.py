"""The supported UI languages and how a user's language is decided.

'en' is the catalog key language (English text IS the key, see Translator);
'gsw' (Züridütsch) is never reported by Telegram clients - it is reachable
only through the explicit /language picker.
"""

SUPPORTED_LANGUAGES = ('en', 'de', 'gsw', 'fr', 'it')
DEFAULT_LANGUAGE = 'en'

# Each language named in itself - a user lost in the wrong language must still
# recognize their own entry in the picker.
NATIVE_NAMES = {
    'en': 'English',
    'de': 'Deutsch',
    'gsw': 'Züridütsch',
    'fr': 'Français',
    'it': 'Italiano',
}


def normalize(telegram_language_code: str | None) -> str | None:
    """A Telegram client language_code ('de-CH', 'fr', 'en-US', ...) mapped to a
    supported language, or None if we don't cover it."""
    if not telegram_language_code:
        return None
    primary_subtag = telegram_language_code.lower().split('-')[0]
    return primary_subtag if primary_subtag in SUPPORTED_LANGUAGES else None


def resolve_user_language(saved_language: str | None, telegram_language_code: str | None) -> str:
    """An explicit /language choice wins; otherwise the client's UI language;
    otherwise English. The client code arrives with every update, so unset users
    self-heal without any migration."""
    if saved_language in SUPPORTED_LANGUAGES:
        return saved_language
    return normalize(telegram_language_code) or DEFAULT_LANGUAGE
