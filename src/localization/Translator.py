"""THE translation seam: every user-facing literal is wrapped in t() at its
composition site (never at import time - module constants stay English so they
can't freeze a language at startup).

Catalog format: locales/<language>.json, flat, the exact English string is the
key. English needs no file - the key is the text. Dynamic parts are named
{placeholders}; callers pass them as kwargs, already HTML-escaped where needed
(catalog values may contain our own HTML markup, so t() never escapes).

Fail-open on every miss: unknown key or a translation whose placeholders don't
match falls back to the English text, logged - never raised.
"""
import json
import logging
import os

from localization.LanguageContext import current_language
from localization.Languages import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

_LOCALES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'locales')


def _load_catalogs() -> dict[str, dict[str, str]]:
    catalogs = {}
    for language in SUPPORTED_LANGUAGES:
        if language == DEFAULT_LANGUAGE:
            continue
        with open(os.path.join(_LOCALES_PATH, f'{language}.json'), encoding='utf-8') as file:
            catalogs[language] = json.load(file)
    return catalogs


_catalogs = _load_catalogs()


def translate(text: str, language: str) -> str:
    """The raw catalog lookup for one explicit language, without formatting."""
    if language == DEFAULT_LANGUAGE:
        return text
    translated = _catalogs.get(language, {}).get(text)
    if translated is None:
        logging.warning('Missing %s translation for: %.80s', language, text)
        return text
    return translated


def t(text: str, **params) -> str:
    """The English text translated into the ambient language, with {placeholders}
    filled from params."""
    template = translate(text, current_language())
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        # The translation's placeholders drifted from the English key -
        # fall back to the (known-good) English template.
        logging.warning('Placeholder mismatch in %s translation of: %.80s', current_language(), text)
        return text.format(**params)
