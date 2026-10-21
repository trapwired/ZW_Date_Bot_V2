"""The calendar subscription's use cases (plan §3, §6): issue or rotate a member's
personal feed link, report its status, and render the feed a link points at.

Telegram-free and HTTP-free: the bot replies and the aiohttp routes both sit on top."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

import pandas as pd

from Enums import Audience

from data.TenantContext import team_context

from domain.EventVisibility import visible_event_types
from domain.Season import get_current_season_dates
from domain.calendar import Tokens
from domain.calendar.CalendarFeed import build_feed_entries
from domain.calendar.Ics import render_calendar

from localization.LanguageContext import language_context

from Utils import DateTimeUtils
from Utils.CustomExceptions import ObjectNotFoundException

GOOGLE_SUBSCRIBE_URL = 'https://www.google.com/calendar/render?cid='


@dataclass(frozen=True)
class CalendarFeedConfig:
    public_origin: str
    http_port: int

    @property
    def enabled(self) -> bool:
        # Dormant until the public origin exists (DNS + reverse proxy): no menu row,
        # no HTTP server, /calendar answers «not set up».
        return bool(self.public_origin)

    @classmethod
    def from_api_config(cls, api_config) -> 'CalendarFeedConfig':
        public_origin = api_config.get_key('Calendar', 'public_origin', default='').strip().rstrip('/')
        http_port = int(api_config.get_key('Calendar', 'http_port', default='8080'))
        return cls(public_origin, http_port)


@dataclass(frozen=True)
class IssuedLink:
    # Both carry the raw token: kept out of repr so a log line or error report can't leak it.
    url: str = field(repr=False)
    google_url: str = field(repr=False)


@dataclass(frozen=True)
class LinkStatus:
    created_at: datetime
    last_used_at: datetime | None


class CalendarFeedService:

    def __init__(self, data_access, config: CalendarFeedConfig):
        self.data_access = data_access
        self.config = config

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def issue_link(self, telegram_id: int) -> IssuedLink:
        """A new link for the member; replacing the stored hash is the rotation, so any
        previous link stops working with this call."""
        user = self.data_access.get_user(telegram_id)
        token = Tokens.mint_token()
        self.data_access.replace_calendar_token(user.doc_id, Tokens.hash_token(token), _utc_now())
        url = f'{self.config.public_origin}/cal/{token}.ics'
        return IssuedLink(url=url, google_url=_google_subscribe_url(url))

    def link_status(self, telegram_id: int) -> LinkStatus | None:
        user = self.data_access.get_user(telegram_id)
        token = self.data_access.get_calendar_token(user.doc_id)
        if token is None:
            return None
        return LinkStatus(created_at=token.created_at, last_used_at=token.last_used_at)

    def render_feed(self, file_name: str) -> str | None:
        """The ICS body for a requested `<token>.ics`, or None for every kind of miss
        (malformed, unknown, rotated, member the bot no longer lists events for) - the
        route answers all of them with the same 404. Sync: the route runs it in a thread."""
        raw_token = Tokens.token_from_feed_file_name(file_name)
        if raw_token is None:
            return None
        token_hash = Tokens.hash_token(raw_token)
        token = self.data_access.find_calendar_token_by_hash(token_hash)
        if token is None:
            return None
        try:
            user = self.data_access.get_user_by_doc_id(token.user_id)
            user_to_state = self.data_access.get_user_state_for_user(user)
            # Re-evaluated on every fetch: the same gate as the events menu, so a member who
            # turns inactive or leaves the team loses the feed without the link being touched.
            if not user_to_state.team_id or not Audience.EVERYONE.allows(user_to_state):
                return None
            team = self.data_access.get_team(user_to_state.team_id)
        except ObjectNotFoundException:
            # A dangling row (user, state or team gone) is a miss like any other: a 404, not
            # a 500 on every poll of the calendar app.
            return None
        with team_context(user_to_state.team_id):
            with language_context(user_to_state.language or team.language):
                body = self._render(user, user_to_state, team.name)
        self._stamp_last_used(token_hash)
        return body

    def _render(self, user, user_to_state, team_name: str) -> str:
        since = _season_start()
        # The domain filters by role itself; querying only the visible types just saves
        # the reads (no timekeeping query for spectators).
        events_by_type = {event_type: self.data_access.get_events_since(event_type, since)
                          for event_type in visible_event_types(user_to_state.role)}
        attendances = (self.data_access.get_all_event_attendances(user)
                       if Audience.PLAYERS.allows(user_to_state) else {})
        entries = build_feed_entries(events_by_type, attendances, user_to_state.role, team_name)
        return render_calendar(entries, team_name, _utc_now())

    def _stamp_last_used(self, token_hash: str) -> None:
        # Bookkeeping only: a failed stamp must never cost the member their calendar.
        try:
            self.data_access.touch_calendar_token(token_hash, _utc_now())
        except Exception:
            logging.warning('Could not stamp last_used_at on a calendar token', exc_info=True)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _season_start() -> pd.Timestamp:
    # get_current_season_dates() is naive; get_events_since only accepts an instant.
    naive_start, _ = get_current_season_dates()
    return DateTimeUtils.add_zurich_timezone(pd.Timestamp(naive_start))


def _google_subscribe_url(feed_url: str) -> str:
    # Telegram only accepts http(s) in URL buttons, so the webcal:// variant travels
    # inside Google's (undocumented) subscribe link instead of being linked directly.
    webcal_url = urlsplit(feed_url)._replace(scheme='webcal').geturl()
    return GOOGLE_SUBSCRIBE_URL + quote(webcal_url, safe='')
