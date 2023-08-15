from src.databaseEntities.Game import Game


def pretty_print_game_stats(game_stats: (list, list, list)):
    yes, no, unsure = game_stats
    return f'{len(yes)}Y / {len(no)}N / {len(unsure)}U'


def pretty_print_game(game: Game, game_stats: (list, list, list)) -> str:
    short_game_stats = pretty_print_game_stats(game_stats)
    return f'{game.timestamp.strftime("%d.%m.%Y %H:%M")} | {game.location} | {short_game_stats}'


def pretty_print_game_summary(stats: (list, list, list), game_string: str) -> str:
    yes, no, unsure = stats
    total_players = len(yes) + len(no) + len(unsure)
    result = game_string + '\n\n'
    result += f'\tTeam / Yes ({len(yes)}/{total_players})\n'
    for player in yes:
        result += f'\t\t{player.firstname} {player.lastname[0]}\n'
    result += '\n\n'
    result += f'\tNo ({len(no)}/{total_players})\n'
    for player in no:
        result += f'\t\t{player.firstname} {player.lastname[0]}\n'
    result += '\n\n'
    result += f'\tUnsure ({len(unsure)}/{total_players})\n'
    for player in unsure:
        result += f'\t\t{player.firstname} {player.lastname[0]}\n'
    return result
