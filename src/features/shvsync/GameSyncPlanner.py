"""Pure diff between the SHV schedule and the bot's games - no I/O, fully unit-testable.

Matching rules (the deciding factor for "exists vs. moved" is the opponent):
1. A bot game with the same shv_game_id IS that game - apply any date/venue change.
2. Otherwise a not-yet-linked bot game with the same (normalized) opponent is the
   same game, just entered manually or moved - link it and apply the SHV data.
   With several candidates (home and away round share the opponent) the one
   closest in time wins.
3. No match at all: a genuinely new game.

Bot games that are linked but no longer in the SHV feed are reported as vanished -
they are NOT deleted (attendance answers hang off them); the admins decide.
"""
from dataclasses import dataclass

import pandas as pd

from domain.entities.Game import Game
from features.shvsync.ShvApiClient import ShvGame


@dataclass(frozen=True)
class GameUpdate:
    """A bot game the SHV schedule changed, with the old values for the notification."""
    game: Game  # carries the existing doc_id with the SHV data applied
    old_timestamp: pd.Timestamp
    old_location: str


@dataclass(frozen=True)
class SyncPlan:
    to_add: list[Game]
    to_update: list[GameUpdate]
    vanished: list[Game]

    def has_changes(self) -> bool:
        return bool(self.to_add or self.to_update or self.vanished)


def plan(shv_games: list[ShvGame], bot_games: list[Game]) -> SyncPlan:
    by_shv_id = {game.shv_game_id: game for game in bot_games if game.shv_game_id is not None}
    unlinked = [game for game in bot_games if game.shv_game_id is None]

    to_add, to_update = [], []
    for shv_game in shv_games:
        existing = by_shv_id.get(shv_game.shv_game_id)
        if existing is None:
            existing = _adopt_by_opponent(unlinked, shv_game)
        if existing is None:
            to_add.append(Game(shv_game.timestamp, shv_game.location, shv_game.opponent,
                               shv_game.shv_game_id))
        elif _differs(existing, shv_game):
            updated = Game(shv_game.timestamp, shv_game.location, shv_game.opponent,
                           shv_game.shv_game_id, doc_id=existing.doc_id)
            to_update.append(GameUpdate(updated, existing.timestamp, existing.location))

    seen_ids = {shv_game.shv_game_id for shv_game in shv_games}
    vanished = [game for game in bot_games
                if game.shv_game_id is not None and game.shv_game_id not in seen_ids]
    return SyncPlan(to_add, to_update, vanished)


def _adopt_by_opponent(unlinked: list[Game], shv_game: ShvGame) -> Game | None:
    candidates = [game for game in unlinked
                  if _normalize(game.opponent) == _normalize(shv_game.opponent)]
    if not candidates:
        return None
    match = min(candidates, key=lambda game: abs(game.timestamp - shv_game.timestamp))
    # Each bot game can adopt at most one SHV game (home and away round share the opponent).
    unlinked.remove(match)
    return match


def _differs(existing: Game, shv_game: ShvGame) -> bool:
    # A freshly adopted game differs by definition: the shv_game_id link must be persisted.
    return (existing.shv_game_id != shv_game.shv_game_id
            or existing.timestamp != shv_game.timestamp
            or existing.location != shv_game.location)


def _normalize(opponent: str) -> str:
    return ' '.join(opponent.casefold().split())
