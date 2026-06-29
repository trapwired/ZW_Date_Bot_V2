"""Application service for the website slice: the URL shown to players, and the
admin flow that stages and commits a new URL.

The pending URL an admin types is staged in their state's ``additional_info``;
committing or discarding it always clears that field so a saved URL can't be
re-applied. Presentation (markup, messages) stays in the nodes.
"""
from Data.DataAccess import DataAccess

from databaseEntities.UsersToState import UsersToState


class WebsiteService:
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def get_url(self) -> str | None:
        return self.data_access.get_website()

    def commit_pending_url(self, telegram_id: int) -> tuple[str, UsersToState]:
        user_to_state, pending_url = self._take_pending(telegram_id)
        self.data_access.set_website(pending_url)
        return pending_url, user_to_state

    def discard_pending_url(self, telegram_id: int) -> UsersToState:
        user_to_state, _ = self._take_pending(telegram_id)
        return user_to_state

    def _take_pending(self, telegram_id: int) -> tuple[UsersToState, str]:
        user_to_state = self.data_access.get_user_state(telegram_id)
        pending_url = user_to_state.additional_info
        user_to_state.additional_info = ''
        return user_to_state, pending_url
