import datetime

from multipledispatch import dispatch

from databaseEntities.TimekeepingEvent import TimekeepingEvent
from databaseEntities.Training import Training
from databaseEntities.Attendance import Attendance
from databaseEntities.Game import Game
from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.TempData import TempData

from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from Enums.CallbackOption import CallbackOption

from Utils import UpdateEventUtils

from databaseEntities.PlayerMetric import PlayerMetric


def pretty_print_game_stats(game_stats: (list, list, list), attendance: Attendance | None):
    yes, no, unsure = game_stats
    yes_string = add_attendance_marks(f'{len(yes)}Y', attendance, AttendanceState.YES)
    no_string = add_attendance_marks(f'{len(no)}N', attendance, AttendanceState.NO)
    unsure_string = add_attendance_marks(f'{len(unsure)}U', attendance, AttendanceState.UNSURE)
    return f'{yes_string} / {no_string} / {unsure_string}'


def pretty_print_timekeeping_stats(tke_stats: (list, list, list), attendance: Attendance | None):
    yes, no, unsure = tke_stats
    result = add_attendance_marks(f'{len(yes)}Y', attendance, AttendanceState.YES)
    if len(yes) >= 2:
        result += ' (Enough)'
    return result


def add_attendance_marks(text: str, attendance: Attendance | None, attendance_state: AttendanceState):
    at_bef, at_aft = get_attendance_symbols(attendance)
    if not attendance:
        if attendance_state is AttendanceState.UNSURE:
            return at_bef + text + at_aft
        else:
            return text

    if attendance.state == attendance_state:
        return at_bef + text + at_aft
    return text


def get_attendance_symbols(attendance: Attendance | None) -> (str, str):
    attendance_before = '👉'
    attendance_after = '👈'
    return attendance_before, attendance_after


def get_update_attribute_message(attribute: CallbackOption) -> str:
    if attribute == CallbackOption.SAVE:
        message = (f'Review your changes in the message above - if all data is correct, use the button \'SAVE\' or type'
                   f' \'save\' to store the event. Use the other buttons to \'RESTART\' or \'CANCEL\'...')
    else:
        message = f'Send me the new {attribute.name.title()} in the following form:\n'
        message += f'{UpdateEventUtils.get_input_format_string(attribute)}\n'
        message += 'To cancel updating, just send me /cancel'
    return message


def pretty_print_event_stats(event_stats: (list, list, list), event_type: Event, attendance: Attendance | None):
    match event_type:
        case Event.GAME:
            return pretty_print_game_stats(event_stats, attendance)
        case Event.TRAINING:
            return pretty_print_game_stats(event_stats, attendance)
        case Event.TIMEKEEPING:
            return pretty_print_timekeeping_stats(event_stats, attendance)


def pretty_print_event_datetime(event: Game | Training | TimekeepingEvent):
    return f'{event.__class__.__name__.title()} - {event.timestamp.strftime("%d.%m.%Y %H:%M")}'


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


@dispatch(TempData, Event)
def pretty_print(temp_data: TempData, event_type: Event) -> str:
    timestamp = temp_data.timestamp if temp_data.timestamp else UpdateEventUtils.parse_datetime_string('01.01.2000 00:00')
    opponent = temp_data.opponent if temp_data.opponent else 'XXX'
    location = temp_data.location if temp_data.location else 'XXX'
    match event_type:
        case Event.GAME:
            return pretty_print_long(Game(timestamp, location, opponent))
        case Event.TRAINING:
            return pretty_print(Training(timestamp, location))
        case Event.TIMEKEEPING:
            return pretty_print(TimekeepingEvent(timestamp, location))


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


def create_game_summary(game: Game) -> str:
    when_str = game.timestamp.strftime('%H:%M')
    meeting_time = game.timestamp - datetime.timedelta(minutes=45)
    meeting_time_str = meeting_time.strftime('%H:%M')
    maps_search_part = '+'.join(game.location.strip().split(' '))
    maps_link = f'https://www.google.com/maps/search/{maps_search_part}'

    summary = (f'Just a quick reminder for the game today:\n'
               f'_When:_ {when_str} o\'clock\n'
               f'_Meeting time:_ *{meeting_time_str}, ready in the changing room*\n'
               f'_Where:_ {game.location.title()} \\([Google Maps]({maps_link})\\)\n'
               f'_Opponent:_ {game.opponent.title()}\n'
               f'_Jerseys:_ Don\'t forget to bring them, \\(whoever has them\\.\\.\\.\\)')
    return summary


def create_training_summary(training: Training) -> str:
    when_str = training.timestamp.strftime('%H:%M')
    maps_search_part = '+'.join(training.location.strip().split(' '))
    maps_link = f'https://www.google.com/maps/search/{maps_search_part}'

    summary = (f'Just a quick reminder for the training tomorrow:\n'
               f'_When:_ {when_str} o\'clock\n'
               f'_Where:_ {training.location.title()} \\([Google Maps]({maps_link})\\)\n'
               f'Please be there on time, so we can use the full 90min to train\\.\\.\\.\\')
    return summary


def pretty_print_player_name(player: TelegramUser) -> str:
    res = f'\t\t{player.firstname.capitalize()}'
    if player.lastname:
        res += f' {player.lastname[0].capitalize()}.'
    res += '\n'
    return res


def pretty_print_player_metric(player_metric: PlayerMetric) -> str:
    return (f'G:{player_metric.game_reminders_sent}, T:{player_metric.training_reminders_sent}, '
            f'TKE: {player_metric.timekeeping_reminders_sent}')


def create_sorted_dict(user_to_player_metrics_dict) -> []:
    result_list = []
    for key, value in user_to_player_metrics_dict.items():
        total_reminders = value.sum_values()
        result_list.append((total_reminders, key, value))
    result_list.sort(key=lambda x: x[0], reverse=True)
    return result_list


def create_sorted_event_attendance_dict(user_to_event_attendances_dict) -> []:
    result_list = []
    for user, all_attendances in user_to_event_attendances_dict.items():
        total_yes = sum(x.state == AttendanceState.YES for x in all_attendances)
        result_list.append((total_yes, user, all_attendances))
    result_list.sort(key=lambda x: x[0])
    return result_list


def pretty_print_statistics(user_to_player_metrics_dict: dict):
    result = 'Statistics:\n\n'
    result += '\tReminders sent (Game, Training, Timekeeping-Event):\n'
    sorted_list = create_sorted_dict(user_to_player_metrics_dict)
    for element in sorted_list:
        total_reminders, key, value = element
        player_name = pretty_print_player_name(key)[0:-1]
        statistics = pretty_print_player_metric(value)
        result += f'\t\t{player_name} ({str(total_reminders)})\t\t{statistics}\n'
    return result


def pretty_print_event_statistics(game_statistics: dict, event_type: Event):
    event_type_string = event_type.name.lower()
    result = f'{event_type_string.title()}-Statistics:\n\n'
    result += f'\tPlayer attendance for all {event_type_string}s this season (so far):\n'
    sorted_list = create_sorted_event_attendance_dict(game_statistics)

    for element in sorted_list:
        total_attendances, user, _ = element
        player_name = pretty_print_player_name(user)[0:-1]
        result += f'\t\t{player_name}: {str(total_attendances)}\n'
    return result


def prepare_message(message: str):
    # Escape characters for markdownV2
    escape_chars = '.|()#_!-+\\><=~*{}[]'
    doubles = '*'

    result = ''
    one_line = ''
    doubles_dict = build_doubles_dict(doubles)
    line_split = message.splitlines()
    for line in line_split:
        for char in line:
            if char in escape_chars:
                if char in doubles_dict.keys():
                    doubles_dict[char] += 1
        for char in line:
            if char in escape_chars:
                if char in doubles_dict.keys():
                    if doubles_dict[char] % 2 == 1:
                        one_line += '\\'
                else:
                    one_line += '\\'
            one_line += char
        result += one_line + '\n'
        # reset values
        doubles_dict = build_doubles_dict(doubles)
        one_line = ''

    # max length is 4096 chars - split into multiple messages
    result_list = []
    while len(result) > 4096:
        result_list.append(result[:4095])
        result = result[4095:]
    result_list.append(result)

    return result_list


def build_doubles_dict(doubles: str):
    res = {}
    for char in doubles:
        res[char] = 0
    return res
