# A game-day squad is at most 9 players; once cancellations leave only that many
# available, the trainers need to know.
MAX_PLAYERS_PER_GAME = 9


def has_too_few_available_players(available_player_count: int) -> bool:
    return available_player_count <= MAX_PLAYERS_PER_GAME
