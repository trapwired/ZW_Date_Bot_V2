"""Pure diff between the SHV schedule and the bot's games - no I/O, fully unit-testable.

Matching tiers per SHV game (first hit wins, each bot game matches at most once):
1. Same `shv_game_id` IS that game - any date/venue change is applied automatically.
2. A not-yet-linked bot game with the same (normalized) opponent is the same game,
   entered manually - adopted and updated automatically. With several candidates
   (home and away round share the opponent) the one closest in time wins.
3. A not-yet-linked bot game on the same calendar date but a DIFFERENT opponent
   might be the same game under another spelling - that is a question for the
   admins, not an automatic action (unless they already declined this exact pair).
4. No match at all: a question to import a new game.

Bot games left over afterwards are questions too: linked ones vanished from the
feed (delete?), unlinked ones were never on SHV (delete, or keep as manual game?).
Games the admins decided to keep (`kept_manual_doc_ids`) stay out of the matching
entirely - a declared friendly must never be adopted by a league game.
"""
from dataclasses import dataclass

import pandas as pd

from domain.entities.Game import Game
from features.shvsync.ShvApiClient import ShvGame


@dataclass(frozen=True)
class GameUpdate:
    """A bot game the SHV schedule changed, with the old values for the report."""
    game: Game  # carries the existing doc_id with the SHV data applied
    old_timestamp: pd.Timestamp
    old_location: str


@dataclass(frozen=True)
class AdoptQuestion:
    """Same date, different opponent: 'is this the same game?' for the admins."""
    bot_game: Game
    shv_game: ShvGame


@dataclass(frozen=True)
class SyncPlan:
    auto_updates: list[GameUpdate]
    adopt_questions: list[AdoptQuestion]
    new_games: list[ShvGame]          # candidate imports (create questions)
    vanished: list[Game]              # linked bot games gone from the feed (delete questions)
    manual_leftovers: list[Game]      # unlinked bot games never on SHV (delete/keep questions)


def plan(shv_games: list[ShvGame], bot_games: list[Game],
         declined_adopt_pairs: set[tuple[int, str]] = frozenset(),
         kept_manual_doc_ids: set[str] = frozenset()) -> SyncPlan:
    by_shv_id = {game.shv_game_id: game for game in bot_games if game.shv_game_id is not None}
    unlinked = [game for game in bot_games
                if game.shv_game_id is None and game.doc_id not in kept_manual_doc_ids]

    auto_updates, adopt_questions, new_games = [], [], []
    for shv_game in shv_games:
        existing = by_shv_id.get(shv_game.shv_game_id) or _match_by_opponent(unlinked, shv_game)
        if existing is not None:
            if _differs(existing, shv_game):
                auto_updates.append(GameUpdate(_applied(existing, shv_game),
                                               existing.timestamp, existing.location))
            continue
        candidate = _match_by_date(unlinked, shv_game, declined_adopt_pairs)
        if candidate is not None:
            adopt_questions.append(AdoptQuestion(candidate, shv_game))
            continue
        new_games.append(shv_game)

    seen_ids = {shv_game.shv_game_id for shv_game in shv_games}
    vanished = [game for game in bot_games
                if game.shv_game_id is not None and game.shv_game_id not in seen_ids]
    return SyncPlan(auto_updates, adopt_questions, new_games, vanished, manual_leftovers=unlinked)


def apply_shv_data(bot_game: Game, shv_game: ShvGame) -> Game:
    """The bot game with the SHV data (incl. the id link) applied - one definition
    of 'mirror the SHV feed' for the automatic path and the admin-confirmed adoption."""
    return _applied(bot_game, shv_game)


def _applied(bot_game: Game, shv_game: ShvGame) -> Game:
    return Game(shv_game.timestamp, shv_game.location, shv_game.opponent,
                shv_game.shv_game_id, doc_id=bot_game.doc_id)


def _match_by_opponent(unlinked: list[Game], shv_game: ShvGame) -> Game | None:
    candidates = [game for game in unlinked
                  if _normalize(game.opponent) == _normalize(shv_game.opponent)]
    return _take_closest(unlinked, candidates, shv_game)


def _match_by_date(unlinked: list[Game], shv_game: ShvGame,
                   declined_adopt_pairs: set[tuple[int, str]]) -> Game | None:
    candidates = [game for game in unlinked
                  if game.timestamp.date() == shv_game.timestamp.date()
                  and (shv_game.shv_game_id, game.doc_id) not in declined_adopt_pairs]
    return _take_closest(unlinked, candidates, shv_game)


def _take_closest(unlinked: list[Game], candidates: list[Game], shv_game: ShvGame) -> Game | None:
    if not candidates:
        return None
    match = min(candidates, key=lambda game: abs(game.timestamp - shv_game.timestamp))
    # Each bot game can match at most one SHV game (home and away round share the opponent).
    unlinked.remove(match)
    return match


def _differs(existing: Game, shv_game: ShvGame) -> bool:
    # A freshly matched game differs by definition: the shv_game_id link must be persisted.
    return (existing.shv_game_id != shv_game.shv_game_id
            or existing.timestamp != shv_game.timestamp
            or existing.location != shv_game.location)


def _normalize(opponent: str) -> str:
    return ' '.join(opponent.casefold().split())
