from datetime import datetime

from Data.DataAccess import DataAccess

from databaseEntities.Training import Training
from databaseEntities.TelegramUser import TelegramUser
from databaseEntities.Game import Game
from databaseEntities.Attendance import Attendance

from Enums.AttendanceState import AttendanceState
from Enums.Event import Event

PLAYERS = {
    'Name': 42
}


def is_description(line: str):
    return '|' in line


def find_id(line: str):
    for name in PLAYERS.keys():
        if name in line:
            return PLAYERS[name]
    raise Exception('Player not found: ' + line)


class OneTimeSetup():
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access

    def add_all(self):
        self.add_trainings()

    def add_games(self):

        f = open('data.txt', 'r', encoding='utf-8')
        attendance_state = None
        for line in f:
            line = line.strip()
            if is_description(line):
                line_split = line.split('|')
                values = []
                for sep in line_split:
                    values.append(sep.strip())
                new_game = Game(datetime.strptime(values[0], '%d.%m.%Y %H:%M'), values[1], values[2])
                game = self.data_access.add(new_game)
                attendance_state = None
            elif line.startswith('Team / Yes'):
                attendance_state = AttendanceState.YES
            elif line.startswith('No ('):
                attendance_state = AttendanceState.NO
            elif line.startswith('Still Unsure'):
                attendance_state = AttendanceState.UNSURE
            elif len(line) > 2:
                telegram_id = find_id(line)
                self.add_game_attendance(game, telegram_id, attendance_state)
            else:
                print(line)

    def add_game_attendance(self, game: Game, telegram_id: int, attendance: AttendanceState):
        if game is None:
            raise Exception('Game is None')
        telegram_user = self.data_access.get_user(telegram_id)
        new_attendance = Attendance(telegram_user.doc_id, game.doc_id, attendance)

        self.data_access.update_attendance(new_attendance, Event.GAME)

    def add_players(self):
        players = []
        new_player = TelegramUser(42, 'Hans', 'Müller')
        players.append(new_player)

        for player in players:
            self.data_access.add(player)

    def add_trainings(self):
        trainings = []
        # Add Trainings to list
        new_training = Training(datetime(2023, 9, 14, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 9, 26, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 10, 12, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 10, 24, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 11, 9, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 11, 21, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 12, 7, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)
        new_training = Training(datetime(2023, 12, 19, 20, 30), 'Zürich Utogrund')
        trainings.append(new_training)

        # Add trainings to DB
        for training in trainings:
            self.data_access.add(training)
