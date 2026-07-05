"""The ambient language of the current unit of work (update, per-recipient send
in a fan-out loop, per-team scheduled job iteration).

Same shape as data/TenantContext, but fail-OPEN: a send with no language
resolved must go out in English rather than raise - wrong language beats no
message.
"""
from contextlib import contextmanager
from contextvars import ContextVar, Token

from localization.Languages import DEFAULT_LANGUAGE

_current_language: ContextVar[str] = ContextVar('current_language', default=DEFAULT_LANGUAGE)


def set_current_language(language: str) -> Token:
    return _current_language.set(language)


def reset_current_language(token: Token) -> None:
    _current_language.reset(token)


def current_language() -> str:
    return _current_language.get()


@contextmanager
def language_context(language: str):
    token = set_current_language(language)
    try:
        yield
    finally:
        reset_current_language(token)
