from src.databaseEntities.Game import Game


def pretty_print_game_stats(game_stats: (list, list, list)):
    yes, no, unsure = game_stats
    return f'{len(yes)}Y / {len(no)}N / {len(unsure)}U'


def pretty_print_game(game: Game, game_stats: (list, list, list)) -> str:
    short_game_stats = pretty_print_game_stats(game_stats)
    return f'{game.timestamp.strftime("%d.%m.%Y %H:%M")} | {game.location} | {short_game_stats}'