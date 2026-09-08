"""Client for the Swiss Handball Federation (SHV) matchcenter GraphQL API.

The API is the unofficial backend of handball.ch/de/matchcenter (open, no auth) -
it may change without notice, so failures must surface via the maintainer alert,
never pass silently. `objectId` is the stable per-game identifier ('gameId' in the
same payload is always 0, 'gameNumber' is 'prov.' for unconfirmed games).
"""
from dataclasses import dataclass

import httpx
import pandas as pd

from Utils import DateTimeUtils

SHV_API_URL = 'https://www.handball.ch/Umbraco/Api/MatchCenter/Query'

# The site's WAF rejects default library user agents (httpx gets a 403, curl passes),
# so identify as a plain browser.
_REQUEST_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; ZWDateBot/1.0)'}

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


@dataclass(frozen=True)
class ShvGame:
    """One game as the SHV schedule states it (a value object, not a bot entity)."""
    shv_game_id: int
    timestamp: pd.Timestamp  # tz-aware Europe/Zurich
    opponent: str
    location: str
    is_played: bool


async def fetch_games(shv_team_id: int) -> list[ShvGame]:
    async with httpx.AsyncClient(timeout=30, headers=_REQUEST_HEADERS) as client:
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
