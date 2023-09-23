from multipledispatch import dispatch

from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training
from databaseEntities.Attendance import Attendance
from databaseEntities.Game import Game

from Enums.Event import Event
from Enums.AttendanceState import AttendanceState

from databaseEntities.TelegramUser import TelegramUser


def pretty_print_game_stats(game_stats: (list, list, list)):
    yes, no, unsure = game_stats
    return f'{len(yes)}Y / {len(no)}N / {len(unsure)}U'


def pretty_print_timekeeping_stats(tke_stats: (list, list, list)):
    yes, no, unsure = tke_stats
    result = f'{len(yes)}Y'
    if len(yes) >= 2:
        result += ' (Enough)'
    return result


def pretty_print_event_stats(event_stats: (list, list, list), event_type: Event):
    match event_type:
        case Event.GAME:
            return pretty_print_game_stats(event_stats)
        case Event.TRAINING:
            return pretty_print_game_stats(event_stats)
        case Event.TIMEKEEPING:
            return pretty_print_timekeeping_stats(event_stats)


@dispatch(Game)
def pretty_print(game: Game) -> str:
    return f'{game.timestamp.strftime("%d.%m.%Y %H:%M")} | {game.location.title()}'


@dispatch(Game)
def pretty_print_long(game: Game) -> str:
    return f'{game.timestamp.strftime("%d.%m.%Y %H:%M")} | {game.location.title()} | {game.opponent.title()}'


@dispatch(Game, Attendance)
def pretty_print(game: Game, attendance: Attendance) -> str:
    return pretty_print(game) + f' | {attendance.state.name}'


@dispatch(Game, AttendanceState)
def pretty_print(game: Game, attendance: AttendanceState) -> str:
    return pretty_print(game) + f' | {attendance.name}'


@dispatch(Training)
def pretty_print(training: Training) -> str:
    return f'{training.timestamp.strftime("%d.%m.%Y %H:%M")} | {training.location.title()}'


@dispatch(Training, Attendance)
def pretty_print(training: Training, attendance: Attendance) -> str:
    return pretty_print(training) + f' | {attendance.state.name}'


@dispatch(Training, AttendanceState)
def pretty_print(training: Training, attendance: AttendanceState) -> str:
    return pretty_print(training) + f' | {attendance.name}'


@dispatch(TimekeepingEvent)
def pretty_print(tke: TimekeepingEvent) -> str:
    return f'{tke.timestamp.strftime("%d.%m.%Y %H:%M")} | {tke.location.title()}'


@dispatch(TimekeepingEvent, Attendance)
def pretty_print(tke: TimekeepingEvent, attendance: Attendance = None) -> str:
    return pretty_print(tke) + f' | {attendance.state.name}'


@dispatch(TimekeepingEvent, AttendanceState)
def pretty_print(tke: TimekeepingEvent, attendance: AttendanceState) -> str:
    return pretty_print(tke) + f' | {attendance.name}'


def pretty_print_event_summary(stats: (list, list, list), game_string: str, event_type: Event) -> str:
    yes, no, unsure = stats
    total_players = len(yes) + len(no) + len(unsure)
    result = game_string + '\n\n'
    if len(yes) > 0:
        result += f'*\tYes ({len(yes)}/{total_players})*\n'
        for player in yes:
            result += pretty_print_player_name(player)
        result += '\n'

    if event_type is Event.TIMEKEEPING:
        if len(yes) == 0:
            result += '\t\tNoone indicated yes until now :('
        return result

    if len(no) > 0:
        result += f'*\tNo ({len(no)}/{total_players})*\n'
        for player in no:
            result += pretty_print_player_name(player)
        result += '\n'
    if len(unsure) > 0:
        result += f'*\tUnsure ({len(unsure)}/{total_players})*\n'
        for player in unsure:
            result += pretty_print_player_name(player)
    return result


def pretty_print_player_name(player: TelegramUser) -> str:
    res = f'\t\t{player.firstname.capitalize()}'
    if player.lastname:
        res += f' {player.lastname[0].capitalize()}.'
    res += '\n'
    return res


def prepare_message(message: str):
    # Escape characters for markdownV2
    escape_chars = '.|()#_!-+\\><='
    result = ''
    for char in message:
        if char in escape_chars:
            result += "\\"
        result += char
    # max length is 9500 chars
    result = result[:9499]
    return result
