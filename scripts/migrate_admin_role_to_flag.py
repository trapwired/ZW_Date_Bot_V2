"""One-off migration for ADR 0005: admin stops being a Role and becomes the
orthogonal isAdmin flag on users_to_state.

Run ON THE DROPLET, WITH THE BOT STOPPED, against the real credentials:

    ./venv/bin/python scripts/migrate_admin_role_to_flag.py

Every users_to_state document with the legacy role 42 (ADMIN) is rewritten to
role 0 (PLAYER) + isAdmin=true; every other document gets isAdmin=false so the
Firestore equality query get_admins_to_state ("isAdmin" == True) never has to
reason about missing fields.

The entity layer self-heals stragglers on read, but Firestore queries filter on
the STORED values ("role" == PLAYER for reminders/overviews, "isAdmin" == True
for the admin list), so unmigrated admins would silently drop out of the roster
until this ran. Idempotent - safe to re-run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from firebase_admin import credentials, firestore
import firebase_admin

from Enums.Role import Role, LEGACY_ADMIN_ROLE_VALUE
from Enums.Table import Table
from data.Tables import Tables
from Utils import PathUtils
from Utils.ApiConfig import ApiConfig


def build_db():
    api_config = ApiConfig()
    credentials_path = PathUtils.get_secrets_file_path(api_config.get_key('Firebase', 'credentialsFileName'))
    cred_object = credentials.Certificate(credentials_path)
    try:
        default_app = firebase_admin.get_app()
    except ValueError:
        default_app = firebase_admin.initialize_app(cred_object)
    return firestore.client(default_app), api_config


def main():
    db, api_config = build_db()
    tables = Tables(api_config)
    collection = db.collection(tables.get(Table.USERS_TO_STATE_TABLE))

    migrated_admins = 0
    stamped_non_admins = 0
    for doc in collection.get():
        data = doc.to_dict()
        if int(data.get('role')) == LEGACY_ADMIN_ROLE_VALUE:
            collection.document(doc.id).update({'role': int(Role.PLAYER), 'isAdmin': True})
            migrated_admins += 1
        elif 'isAdmin' not in data:
            collection.document(doc.id).update({'isAdmin': False})
            stamped_non_admins += 1

    print(f'done: {migrated_admins} admin(s) moved to PLAYER+isAdmin, '
          f'{stamped_non_admins} document(s) stamped isAdmin=false')


if __name__ == '__main__':
    main()
