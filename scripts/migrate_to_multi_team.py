"""One-off repartition of the flat single-team Firestore layout into per-team
subcollections (ADR 0003).

Run ON THE DROPLET, WITH THE BOT STOPPED, against the real credentials:

    ./venv/bin/python scripts/migrate_to_multi_team.py

The nine domain collections move from the flat root into
teams/{teamId}/<same collection name>; document ids are preserved because
cross-references (Attendance.eventId, PlayerMetric.userId, Attendance.userId)
are stored as doc ids. Identity stays global: users_to_state gains a teamId
field, users is untouched.

The script is idempotent (every write is a set()/update() to a deterministic
target) so it is safe to re-run. It NEVER deletes the flat collections - those
remain as the rollback path and are removed manually once the new layout is
trusted.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from firebase_admin import credentials, firestore
import firebase_admin
from google.cloud.firestore_v1 import FieldFilter

from Enums.Role import Role
from Enums.Table import Table
from data.Tables import Tables
# TEAM_SCOPED_TABLES is the single source of truth for "which collections move"
# (the nine domain tables); reusing it keeps this script from drifting from the
# repository's own tenancy classification.
from data.FirebaseRepository import TEAM_SCOPED_TABLES
from domain.entities.Team import Team
from Utils import PathUtils
from Utils.ApiConfig import ApiConfig

TEAM_NAME = 'Züri West'


def build_db():
    api_config = ApiConfig()
    credentials_path = PathUtils.get_secrets_file_path(api_config.get_key('Firebase', 'credentialsFileName'))
    cred_object = credentials.Certificate(credentials_path)
    try:
        default_app = firebase_admin.get_app()
    except ValueError:
        default_app = firebase_admin.initialize_app(cred_object)
    return firestore.client(default_app), api_config


def flat_collection(db, tables: Tables, table: Table):
    return db.collection(tables.get(table))


def team_subcollection(db, tables: Tables, table: Table, team_id: str):
    return (db.collection(tables.get(Table.TEAMS_TABLE))
            .document(team_id)
            .collection(tables.get(table)))


def resolve_or_create_team(db, tables: Tables, api_config: ApiConfig) -> str:
    # The team's identity anchor is the MEMBERSHIP group ([Telegram] group_chat_id -
    # the chat InitNode gates /start against). Group-message routing reads the same
    # field from the team doc at runtime; the former [Chat_Ids] GROUP_CHAT routing
    # key is retired.
    group_chat_id = int(api_config.get_key('Telegram', 'group_chat_id'))
    teams_col = db.collection(tables.get(Table.TEAMS_TABLE))

    existing = list(teams_col.where(filter=FieldFilter('groupChatId', '==', group_chat_id)).stream())
    if len(existing) == 1:
        print(f'Reusing existing team doc {existing[0].id} (groupChatId={group_chat_id})')
        return existing[0].id
    if len(existing) > 1:
        print(f'FAIL: {len(existing)} teams already share groupChatId={group_chat_id}; refusing to guess')
        sys.exit(1)

    team = Team(
        name=TEAM_NAME,
        group_chat_id=group_chat_id,
        spectator_password=api_config.get_key('Chats', 'SPECTATOR_PASSWORD'),
        trainers_games=api_config.get_int_list('Chat_Ids', 'TRAINERS_GAMES'),
        trainers_training=api_config.get_int_list('Chat_Ids', 'TRAINERS_TRAINING'),
    )
    _, doc_ref = teams_col.add(team.to_dict())
    print(f'Created team doc {doc_ref.id} (name={TEAM_NAME}, groupChatId={group_chat_id})')
    return doc_ref.id


def copy_collection(db, tables: Tables, table: Table, team_id: str) -> int:
    source = flat_collection(db, tables, table)
    dest = team_subcollection(db, tables, table, team_id)
    copied = 0
    for doc in source.stream():
        dest.document(doc.id).set(doc.to_dict())
        copied += 1
    print(f'  copied {tables.get(table)}: {copied} docs')
    return copied


def stamp_team_on_states(db, tables: Tables, team_id: str) -> int:
    # Only real members get a team; INIT (-1, not yet registered) and REJECTED (999)
    # records are not bound to a team and must not resolve into tenant-scoped reads.
    unbound_roles = {int(Role.INIT), int(Role.REJECTED)}
    stamped = 0
    for doc in flat_collection(db, tables, Table.USERS_TO_STATE_TABLE).stream():
        role = doc.to_dict().get('role')
        if role is None or int(role) in unbound_roles:
            continue
        doc.reference.update({'teamId': team_id})
        stamped += 1
    print(f'Stamped teamId on {stamped} users_to_state docs')
    return stamped


def verify_collection(db, tables: Tables, table: Table, team_id: str) -> bool:
    name = tables.get(table)
    source_docs = {doc.id: doc.to_dict() for doc in flat_collection(db, tables, table).stream()}
    dest = team_subcollection(db, tables, table, team_id)
    dest_docs = {doc.id: doc.to_dict() for doc in dest.stream()}

    if len(source_docs) != len(dest_docs):
        print(f'FAIL {name}: {len(source_docs)} -> {len(dest_docs)} (count mismatch)')
        return False
    if source_docs:
        first_id = next(iter(source_docs))
        if source_docs[first_id] != dest_docs.get(first_id):
            print(f'FAIL {name}: doc {first_id} differs between source and destination')
            return False
    print(f'OK {name}: {len(source_docs)} -> {len(dest_docs)}')
    return True


def main():
    db, api_config = build_db()
    tables = Tables(api_config)

    team_id = resolve_or_create_team(db, tables, api_config)

    print('Copying domain collections into teams/{}/ ...'.format(team_id))
    for table in sorted(TEAM_SCOPED_TABLES):
        copy_collection(db, tables, table, team_id)

    stamp_team_on_states(db, tables, team_id)

    print('Verifying ...')
    all_ok = True
    for table in sorted(TEAM_SCOPED_TABLES):
        all_ok = verify_collection(db, tables, table, team_id) and all_ok
    if not all_ok:
        print('Verification FAILED - the flat collections are untouched; investigate before retrying.')
        sys.exit(1)

    print('Migration complete. The flat collections were NOT deleted - they are the '
          'rollback path. Delete them manually once the new layout is trusted.')


if __name__ == '__main__':
    main()
