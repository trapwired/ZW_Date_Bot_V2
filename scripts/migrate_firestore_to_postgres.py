"""Stage B3: copy every Firestore document into Postgres, preserving doc-ids,
then print a verification report (per-table Firestore vs Postgres counts plus
field-level spot checks). Idempotent - every write is an upsert keyed on the
preserved id, so the script is safe to re-run (the B4 cutover runs it once more
bot-stopped for the final delta).

Run INSIDE the bot container on the VPS (both stores reachable there):

    docker exec -i zwdatebot python scripts/migrate_firestore_to_postgres.py

The Postgres DSN resolves like the app's own default plus the compose service
hostname; override with --dsn if needed.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

import firebase_admin
from firebase_admin import credentials, firestore

from data.PostgresRepository import PostgresRepository, TABLE_SPECS, _to_sql_value
from data.FirebaseRepository import GLOBAL_TABLES
from data.Tables import Tables

from Enums.Table import Table

from Utils import PathUtils
from Utils.ApiConfig import ApiConfig

SETTINGS_TABLES = {Table.SETTINGS_TABLE}


class _DsnConfig:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def get_key(self, section, identifier, default=None):
        return self.dsn if identifier == 'dsn' else default


def build_firestore(api_config: ApiConfig):
    path = PathUtils.get_secrets_file_path(api_config.get_key('Firebase', 'credentialsFileName'))
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app(credentials.Certificate(path))
    return firestore.client(app)


def default_dsn() -> str:
    password = os.environ.get('POSTGRES_PASSWORD', 'zwdatebot')
    return f'postgresql://zwdatebot:{password}@postgres:5432/zwdatebot'


def upsert(pg: PostgresRepository, table: Table, doc_id: str, data: dict, team_id: str | None):
    spec = TABLE_SPECS[table]
    columns, values = ['id'], [doc_id]
    for key, column in spec.columns.items():
        if key in data:
            columns.append(column)
            values.append(_to_sql_value(data[key]))
    if spec.team_scoped:
        columns.append('team_id')
        values.append(team_id)
    if spec.event_type is not None:
        columns.append('event_type')
        values.append(spec.event_type)
    assignments = ', '.join(f'{c} = EXCLUDED.{c}' for c in columns if c != 'id')
    conflict_key = '(team_id, id)' if table in SETTINGS_TABLES else '(id)'
    pg._execute(
        f'INSERT INTO {spec.sql_table} ({", ".join(columns)}) '
        f'VALUES ({", ".join(["%s"] * len(columns))}) '
        f'ON CONFLICT {conflict_key} DO UPDATE SET {assignments}',
        values)


def migrate(db, tables: Tables, pg: PostgresRepository) -> list[tuple[str, str, int]]:
    """Copies everything; returns (table label, team, count) rows for the report."""
    copied = []

    for table in sorted(GLOBAL_TABLES, key=lambda t: t.name):
        docs = list(db.collection(tables.get(table)).stream())
        for doc in docs:
            upsert(pg, table, doc.id, doc.to_dict(), team_id=None)
        copied.append((tables.get(table), '(global)', len(docs)))

    team_ids = [doc.id for doc in db.collection(tables.get(Table.TEAMS_TABLE)).stream()]
    for table in sorted(set(Table) - GLOBAL_TABLES, key=lambda t: t.name):
        for team_id in team_ids:
            docs = list(db.collection(tables.get(Table.TEAMS_TABLE))
                        .document(team_id).collection(tables.get(table)).stream())
            for doc in docs:
                upsert(pg, table, doc.id, doc.to_dict(), team_id=team_id)
            copied.append((tables.get(table), team_id[:8], len(docs)))
    return copied


def verify(db, tables: Tables, pg: PostgresRepository, copied) -> bool:
    """Firestore count vs Postgres count per table, plus per-doc field spot checks
    on the most reference-heavy tables. Returns overall pass/fail."""
    print(f'\n{"table":34}{"team":10}{"firestore":>10}{"postgres":>10}  ok')
    ok = True
    pg_counts = {}
    for table in Table:
        spec = TABLE_SPECS[table]
        rows = pg._execute(f'SELECT count(*) FROM {spec.sql_table}'
                           + (' WHERE event_type = %s' if spec.event_type is not None else ''),
                           (spec.event_type,) if spec.event_type is not None else None).fetchone()
        pg_counts[table] = rows[0]

    fs_totals = {}
    for label, team, count in copied:
        fs_totals[label] = fs_totals.get(label, 0) + count
    for table in Table:
        label = tables.get(table)
        match = fs_totals.get(label, 0) == pg_counts[table]
        ok &= match
        print(f'{label:34}{"":10}{fs_totals.get(label, 0):>10}{pg_counts[table]:>10}  {"✓" if match else "✗ MISMATCH"}')

    # Spot checks: every users_to_state doc field-for-field, every attendance state.
    spot_ok = True
    uts_spec = TABLE_SPECS[Table.USERS_TO_STATE_TABLE]
    for doc in db.collection(tables.get(Table.USERS_TO_STATE_TABLE)).stream():
        source = doc.to_dict()
        row = pg._execute('SELECT user_id, state, role, is_admin, team_id FROM users_to_state WHERE id = %s',
                          (doc.id,)).fetchone()
        if row is None or row[0] != source.get('userId') or row[1] != int(source.get('state')) \
                or row[2] != int(source.get('role')) or bool(row[3]) != bool(source.get('isAdmin', False)) \
                or row[4] != source.get('teamId'):
            print(f'SPOT-CHECK MISMATCH users_to_state/{doc.id}: {source} vs {row}')
            spot_ok = False
    print(f'spot checks users_to_state: {"✓ all match" if spot_ok else "✗ MISMATCHES"}')
    return ok and spot_ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dsn', default=default_dsn())
    args = parser.parse_args()

    api_config = ApiConfig()
    db = build_firestore(api_config)
    tables = Tables(api_config)
    pg = PostgresRepository(_DsnConfig(args.dsn))

    copied = migrate(db, tables, pg)
    ok = verify(db, tables, pg, copied)
    pg.pool.close()
    print('\nRESULT:', 'VERIFIED ✓' if ok else 'FAILED ✗ - do not cut over')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
