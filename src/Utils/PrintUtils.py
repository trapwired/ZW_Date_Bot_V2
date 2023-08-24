from databaseEntities.Game import Game

from multipledispatch import dispatch

from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training


def pretty_print_game_stats(game_stats: (list, list, list)):
    yes, no, unsure = game_stats
    return f'{len(yes)}Y / {len(no)}N / {len(unsure)}U'


@dispatch(Game)
def pretty_print(game: Game) -> str:
    return f'{game.timestamp.strftime("%d.%m.%Y %H:%M")} | {game.location}'


@dispatch(Training)
def pretty_print(training: Training) -> str:
    return f'{training.timestamp.strftime("%d.%m.%Y %H:%M")} | {training.location}'


@dispatch(TimekeepingEvent)
def pretty_print(tke: TimekeepingEvent) -> str:
    return f'{tke.timestamp.strftime("%d.%m.%Y %H:%M")} | {tke.location}'


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
