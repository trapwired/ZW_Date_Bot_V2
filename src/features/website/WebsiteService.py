"""Application service for the website slice: the URL shown to players, and the
admin flow that stages and commits a new URL.

The pending URL an admin types is staged in their state's ``additional_info``;
committing or discarding it always clears that field so a saved URL can't be
re-applied. Presentation (markup, messages) stays in the nodes.

The URL is rendered as an ``InlineKeyboardButton`` link for players, which
Telegram rejects unless it has an http(s) scheme - so a commit normalizes a
scheme-less host (e.g. ``www.google.com`` -> ``https://www.google.com``) and
refuses anything that still isn't a well-formed http(s) URL, rather than storing
a value that would later blow up when shown.
"""
from urllib.parse import urlparse

from data.DataAccess import DataAccess

from domain.entities.UsersToState import UsersToState


class WebsiteService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_url(self) -> str | None:
        return self.data_access.get_website()

    def commit_pending_url(self, telegram_id: int) -> tuple[str | None, UsersToState]:
        """Persist the staged URL (normalized to an http(s) link) if it is valid.
        Returns the saved URL, or None if the staged value was rejected (the
        staging field is cleared either way)."""
        user_to_state, pending_url = self._take_pending(telegram_id)
        normalized_url = self._normalize_url(pending_url)
        if normalized_url is None:
            return None, user_to_state
        self.data_access.set_website(normalized_url)
        return normalized_url, user_to_state

    def discard_pending_url(self, telegram_id: int) -> UsersToState:
        user_to_state, _ = self._take_pending(telegram_id)
        return user_to_state

    def _take_pending(self, telegram_id: int) -> tuple[UsersToState, str]:
        user_to_state = self.data_access.get_user_state(telegram_id)
        pending_url = user_to_state.additional_info
        user_to_state.additional_info = ''
        return user_to_state, pending_url

    @staticmethod
    def _normalize_url(url: str) -> str | None:
        """Return a well-formed http(s) URL, defaulting a scheme-less host to
        https, or None if the input can't be a valid web link."""
        url = url.strip()
        if not url or any(c.isspace() for c in url):
            return None
        if '://' not in url:
            url = 'https://' + url
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or '.' not in parsed.netloc:
            return None
        return url
