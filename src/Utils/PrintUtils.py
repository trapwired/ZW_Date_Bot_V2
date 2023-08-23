from databaseEntities.Game import Game


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
    if len(yes) > 0:
        result += f'*\tTeam / Yes ({len(yes)}/{total_players})*\n'
        for player in yes:
            result += f'\t\t{player.firstname} {player.lastname[0]}.\n'
        result += '\n'
    if len(no) > 0:
        result += f'*\tNo ({len(no)}/{total_players})*\n'
        for player in no:
            result += f'\t\t{player.firstname} {player.lastname[0]}.\n'
        result += '\n'
    if len(unsure) > 0:
        result += f'*\tUnsure ({len(unsure)}/{total_players})*\n'
        for player in unsure:
            result += f'\t\t{player.firstname} {player.lastname[0]}.\n'
    return result


def escape_message(message: str):
    escape_chars = '.|()#_!-'
    result = ''
    for char in message:
        if char in escape_chars:
            result += "\\"
        result += char
    return result