"""Seed the LOCAL dev Postgres with a synthetic team, players and events - a
predictable playground for trying features (Stage B local-dev requirement).

    docker compose -f deploy/compose.local.yml up -d postgres
    ./venv/bin/python scripts/seed_local_db.py [--telegram-id <your id>]

Idempotent: wipes and re-seeds the whole database (it is a local playground,
never prod - the DSN has no way to point at the VPS, whose postgres publishes
no port). Pass --telegram-id so the seeded admin is YOUR account and the dev
bot's menus respond to you.
"""
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from data.PostgresRepository import PostgresRepository, TABLE_SPECS
from data.TenantContext import set_current_team

from Enums.AttendanceState import AttendanceState
from Enums.Role import Role
from Enums.Table import Table
from Enums.UserState import UserState

from domain.entities.Attendance import Attendance
from domain.entities.Game import Game
from domain.entities.Team import Team
from domain.entities.TelegramUser import TelegramUser
from domain.entities.Training import Training
from domain.entities.UsersToState import UsersToState

LOCAL_DSN = 'postgresql://zwdatebot:zwdatebot@localhost:5434/zwdatebot'

PLAYERS = ['Anna', 'Ben', 'Carla', 'Dario', 'Elin', 'Fabio', 'Gina', 'Hugo']


class _DsnConfig:
    def get_key(self, section, identifier, default=None):
        return LOCAL_DSN if identifier == 'dsn' else default


def main(admin_telegram_id: int):
    repository = PostgresRepository(_DsnConfig())
    tables = ', '.join({spec.sql_table for spec in TABLE_SPECS.values()})
    repository._execute(f'TRUNCATE {tables}')

    team_id = repository.add(Team('ZW Dev Team', group_chat_id=-100999, spectator_password='dev-pass-123'),
                             Table.TEAMS_TABLE)
    set_current_team(team_id)

    user_ids = []
    for n, name in enumerate(PLAYERS):
        user_doc = repository.add(TelegramUser(1000 + n, name, 'Seed'), Table.USERS_TABLE)
        role = Role.RETIRED if n == len(PLAYERS) - 1 else Role.PLAYER
        repository.add(UsersToState(user_doc, UserState.DEFAULT, role=role, team_id=team_id),
                       Table.USERS_TO_STATE_TABLE)
        user_ids.append(user_doc)

    admin_doc = repository.add(TelegramUser(admin_telegram_id, 'You', 'Admin'), Table.USERS_TABLE)
    repository.add(UsersToState(admin_doc, UserState.DEFAULT, role=Role.PLAYER, is_admin=True,
                                team_id=team_id), Table.USERS_TO_STATE_TABLE)

    now = datetime.now()
    for week in range(1, 5):
        game_id = repository.add(Game(now + timedelta(days=7 * week, hours=2),
                                      'Saalsporthalle', f'HC Gegner {week}'), Table.GAMES_TABLE)
        repository.add(Training(now + timedelta(days=7 * week - 3), 'Halle B'), Table.TRAININGS_TABLE)
        for i, user_doc in enumerate(user_ids):
            state = [AttendanceState.YES, AttendanceState.NO, AttendanceState.UNSURE][i % 3]
            repository.add(Attendance(user_doc, game_id, state), Table.GAME_ATTENDANCE_TABLE)

    print(f'seeded: team {team_id}, {len(PLAYERS)} players + 1 admin (telegram id {admin_telegram_id}), '
          f'4 games + 4 trainings with attendance')
    repository.pool.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--telegram-id', type=int, default=206738790,
                        help='your Telegram id - the seeded admin account')
    main(parser.parse_args().telegram_id)
