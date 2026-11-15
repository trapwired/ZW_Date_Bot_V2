"""Client for the Swiss Handball Federation (SHV) matchcenter GraphQL API.

The API is the unofficial backend of handball.ch/de/matchcenter (open, no auth) -
it may change without notice, so failures must surface via the maintainer alert,
never pass silently. `objectId` is the stable per-game identifier ('gameId' in the
same payload is always 0, 'gameNumber' is 'prov.' for unconfirmed games).
"""
import re
import ssl
from dataclasses import dataclass
from pathlib import Path

import certifi
import httpx
import pandas as pd

from Utils import DateTimeUtils

SHV_API_URL = 'https://www.handball.ch/Umbraco/Api/MatchCenter/Query'

# The site's WAF rejects default library user agents (httpx gets a 403, curl passes),
# so identify as a plain browser.
_REQUEST_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; ZWDateBot/1.0)'}

# handball.ch omits its intermediate certificate and OpenSSL does not fetch it, so we ship it.
_MISSING_INTERMEDIATE_CERT = Path(__file__).with_name('ssl_com_tls_issuing_rsa_ca_r1.pem')

_GAMES_QUERY = """
query($teamId: Int) {
  games(teamId: $teamId) {
    objectId gameDateTime homeTeamId homeTeamName awayTeamName venueName gameStatusId
  }
}
"""

_GAME_STATUS_PLAYED = 2


class ShvApiError(Exception):
    """The SHV API answered, but not with the games we asked for."""


_TEAM_URL_PATTERN = re.compile(r'/matchcenter/teams/(\d+)')


def parse_team_id(website: str) -> int | None:
    """The SHV team id from a matchcenter team URL as stored in the team's website
    setting (e.g. https://www.handball.ch/de/matchcenter/teams/36769#/games);
    None when the website is no such URL - the GraphQL API only needs the number."""
    match = _TEAM_URL_PATTERN.search(website)
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class ShvGame:
    """One game as the SHV schedule states it (a value object, not a bot entity)."""
    shv_game_id: int
    timestamp: pd.Timestamp  # tz-aware Europe/Zurich
    opponent: str
    location: str
    is_played: bool


def shv_tls_context() -> ssl.SSLContext:
    context = ssl.create_default_context(cafile=certifi.where())
    context.load_verify_locations(cafile=_MISSING_INTERMEDIATE_CERT)
    return context


async def fetch_games(shv_team_id: int) -> list[ShvGame]:
    async with httpx.AsyncClient(timeout=30, headers=_REQUEST_HEADERS,
                                 verify=shv_tls_context()) as client:
        response = await client.post(
            SHV_API_URL, json={'query': _GAMES_QUERY, 'variables': {'teamId': shv_team_id}})
        response.raise_for_status()
        payload = response.json()
    if payload.get('errors') or 'data' not in payload or payload['data'].get('games') is None:
        raise ShvApiError(f'unexpected SHV response for team {shv_team_id}: {str(payload)[:500]}')
    return [parse_game(game, shv_team_id) for game in payload['data']['games']]


def parse_game(source: dict, shv_team_id: int) -> ShvGame:
    opponent = source['awayTeamName'] if source['homeTeamId'] == shv_team_id \
        else source['homeTeamName']
    # gameDateTime is Zurich wall-clock time without an offset.
    timestamp = DateTimeUtils.add_zurich_timezone(pd.Timestamp(source['gameDateTime']))
    return ShvGame(shv_game_id=int(source['objectId']),
                   timestamp=timestamp,
                   opponent=opponent,
                   location=source['venueName'],
                   is_played=source['gameStatusId'] == _GAME_STATUS_PLAYED)
