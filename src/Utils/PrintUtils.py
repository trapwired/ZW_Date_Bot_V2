import datetime

from multipledispatch import dispatch

from domain.entities.TimekeepingEvent import TimekeepingEvent
from domain.entities.Training import Training
from domain.entities.Attendance import Attendance
from domain.entities.Game import Game
from domain.entities.TelegramUser import TelegramUser
from domain.entities.TempData import TempData

from Enums.Event import Event
from Enums.AttendanceState import AttendanceState
from Enums.EventField import EventField

from Utils import UpdateEventUtils
from Utils import Format

from localization.Translator import t

from domain import EventDateTimeParser

from domain.entities.PlayerMetric import PlayerMetric

EVENT_EMOJI = {Event.GAME: '🤾', Event.TRAINING: '🏃', Event.TIMEKEEPING: '⏱️'}
ATTENDANCE_EMOJI = {AttendanceState.YES: '✅', AttendanceState.NO: '❌', AttendanceState.UNSURE: '❓'}

DATETIME_FORMAT = '%d.%m.%Y %H:%M'


def event_label(event_type: Event) -> str:
    return f'{EVENT_EMOJI[event_type]} {t(event_type.name.title())}'


def _datetime(event) -> str:
    return event.timestamp.strftime(DATETIME_FORMAT)


def get_update_attribute_message(attribute: EventField) -> str:
    if attribute == EventField.SAVE:
        message = t('Review your changes in the message above - if all data is correct, use the button <b>SAVE</b>'
                    ' or type \'save\' to store the event. Use the other buttons to <b>RESTART</b> or '
                    '<b>CANCEL</b>...')
    else:
        message = t('Send me the new {field} in the following form:\n', field=Format.bold(t(attribute.name.title())))
        message += f'{Format.escape(UpdateEventUtils.get_input_format_string(attribute))}\n'
        message += t('To cancel updating, just send me /cancel')
    return message


def pretty_print_event_datetime(event: Game | Training | TimekeepingEvent):
    # Plain text: the only caller passes this as message_extra_text, which get_text escapes.
    return f'{t(event.__class__.__name__.title())} - {_datetime(event)}'


def pretty_print_event_command(event) -> str:
    # PLAIN text (no tags, no escaping): inline-keyboard button labels are rendered
    # literally by Telegram, so HTML markup must never appear here.
    return f'{_datetime(event)} | {event.location.title()}'


_EVENT_TYPES = (Game, Training, TimekeepingEvent)


@dispatch(_EVENT_TYPES)
def pretty_print(event) -> str:
    return f'{Format.bold(_datetime(event))} | {Format.escape(event.location.title())}'


@dispatch(Game)
def pretty_print_long(game: Game) -> str:
    return f'{pretty_print(game)} | {Format.escape(game.opponent.title())}'


@dispatch(_EVENT_TYPES, Attendance)
def pretty_print(event, attendance: Attendance) -> str:
    return f'{pretty_print(event)} | {pretty_print_attendance(attendance.state)}'


@dispatch(_EVENT_TYPES, AttendanceState)
def pretty_print(event, attendance: AttendanceState) -> str:
    return f'{pretty_print(event)} | {pretty_print_attendance(attendance)}'


def pretty_print_attendance(state: AttendanceState) -> str:
    return f'{ATTENDANCE_EMOJI[state]} {t(state.name.title())}'


@dispatch(TempData, Event)
def pretty_print(temp_data: TempData, event_type: Event) -> str:
    timestamp = temp_data.timestamp if temp_data.timestamp else EventDateTimeParser.parse('01.01.2000 00:00').value
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
    result = ''
    if game_string:
        result = game_string + '\n\n'

    result += _attendance_block(ATTENDANCE_EMOJI[AttendanceState.YES], t('Yes'), yes, total_players)

    if event_type is Event.TIMEKEEPING:
        if len(yes) == 0:
            result += '\t\t' + t('Noone indicated yes until now :(')
        return result

    result += _attendance_block(ATTENDANCE_EMOJI[AttendanceState.NO], t('No'), no, total_players)
    result += _attendance_block(ATTENDANCE_EMOJI[AttendanceState.UNSURE], t('Unsure'), unsure, total_players)
    return result


def _attendance_block(emoji: str, label: str, players: list, total_players: int) -> str:
    if len(players) == 0:
        return ''
    block = Format.bold(f'{emoji} {label} ({len(players)}/{total_players})') + '\n'
    for player in players:
        block += pretty_print_player_name(player)
    return block + '\n'


def create_game_summary(game: Game) -> str:
    when_str = game.timestamp.strftime('%H:%M')
    meeting_time = game.timestamp - datetime.timedelta(minutes=45)
    meeting_time_str = meeting_time.strftime('%H:%M')
    location_string = game.location.title().replace('(H)', '').replace('(A)', '').strip()
    maps_link = _maps_link(location_string)

    return t('{emoji} <b>Game today!</b>\n\n'
             '<b>When:</b> {when} o\'clock\n'
             '<b>Meeting:</b> {meeting}, ready in the changing room\n'
             '<b>Where:</b> {where}\n'
             '<b>Opponent:</b> {opponent}\n'
             '<i>Jerseys: do not forget to bring them (whoever has them...)</i>',
             emoji=EVENT_EMOJI[Event.GAME],
             when=Format.escape(when_str),
             meeting=Format.escape(meeting_time_str),
             where=Format.link(location_string, maps_link),
             opponent=Format.escape(game.opponent.title()))


def create_training_summary(training: Training, player_overview: str) -> str:
    when_str = training.timestamp.strftime('%H:%M')
    location_string = training.location.title().replace('(H)', '').replace('(A)', '').strip()
    maps_link = _maps_link(location_string)

    return t('{emoji} <b>Training tomorrow!</b>\n\n'
             '<b>When:</b> {when} o\'clock\n'
             '<b>Where:</b> {where}\n'
             '<b>Who:</b>\n{players}\n'
             'Please be there on time, so we can use the full 90min to train...',
             emoji=EVENT_EMOJI[Event.TRAINING],
             when=Format.escape(when_str),
             where=Format.link(location_string, maps_link),
             players=player_overview)


def _maps_link(location_string: str) -> str:
    maps_search_part = '+'.join(location_string.split(' '))
    return f'https://www.google.com/maps/search/{maps_search_part}'


def sorted_by_display_name(players: [TelegramUser]) -> [TelegramUser]:
    # THE list order for people everywhere in the bot: alphabetical by first name.
    return sorted(players, key=lambda player: get_player_display_name(player).lower())


def get_player_display_name(player: TelegramUser) -> str:
    # Raw (unescaped) name - safe for reply-keyboard buttons. Escape at the call site
    # when embedding into an HTML message.
    name = player.firstname.capitalize()
    if player.lastname:
        name += f' {player.lastname[0].capitalize()}.'
    return name


def pretty_print_player_name(player: TelegramUser) -> str:
    return f'\t\t{Format.escape(get_player_display_name(player))}\n'


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
    result = t('<b>Statistics</b>') + '\n\n'
    result += t('<i>Reminders sent (Game, Training, Timekeeping-Event):</i>') + '\n'
    sorted_list = create_sorted_dict(user_to_player_metrics_dict)
    for element in sorted_list:
        total_reminders, key, value = element
        player_name = Format.escape(get_player_display_name(key))
        statistics = Format.escape(pretty_print_player_metric(value))
        result += f'\t\t{player_name} ({str(total_reminders)})\t\t{statistics}\n'
    return result


def pretty_print_event_statistics(game_statistics: dict, event_type: Event):
    event_type_string = event_type.name.lower()
    result = t('<b>{event_type}-Statistics</b>', event_type=t(event_type_string.title())) + '\n\n'
    result += t('<i>Player attendance for all {event_type}s this season (so far):</i>',
                event_type=event_type_string) + '\n'
    sorted_list = create_sorted_event_attendance_dict(game_statistics)

    for element in sorted_list:
        total_attendances, user, _ = element
        player_name = Format.escape(get_player_display_name(user))
        result += f'\t\t{player_name}: {str(total_attendances)}\n'
    return result


def split_message(message: str) -> list[str]:
    # Telegram caps messages at 4096 chars. Split on line boundaries so HTML tags
    # (which never span lines in our messages) are never cut in half.
    max_length = 4096
    if len(message) <= max_length:
        return [message]

    chunks = []
    current = ''
    for line in message.splitlines(keepends=True):
        while len(line) > max_length:
            if current:
                chunks.append(current)
                current = ''
            chunks.append(line[:max_length])
            line = line[max_length:]
        if len(current) + len(line) > max_length:
            chunks.append(current)
            current = ''
        current += line
    if current:
        chunks.append(current)
    return chunks
