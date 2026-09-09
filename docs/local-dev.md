# Local dev run (Postgres backend)

Run the whole bot locally against test data — confirm before a bigger merge
that everything still works, or try new features. Fully offline from prod.

## One-time setup

1. Create `secrets-local/` in the repo root (gitignored) with one file:
   - `api_config.ini` — copy `secrets/example_api_config.ini`, then set:
     ```ini
     [Telegram]
     api_token = <your DEV bot token from BotFather>

     [Database]
     backend = postgres
     dsn = postgresql://zwdatebot:zwdatebot@postgres:5432/zwdatebot
     ```
     (chat ids → your own Telegram id, like the example.)

## Daily loop

```bash
docker compose -f deploy/compose.local.yml up --build -d
./venv/bin/python scripts/seed_local_db.py --telegram-id <your id>
docker logs -f zwdatebot-local
```

Message your dev bot on Telegram: events menu, admin panel, attendance — all
against the seeded local Postgres. Re-run the seed script anytime for a clean
slate (it truncates and re-seeds).

## Real-data variant (pre-merge confidence)

Restore last night's central VPS backup into the local postgres — real shapes,
and a free restore drill:

```bash
scp ubuntu@179.237.110.135:/srv/backups/<date>/zwdatebot-postgres_pg_dumpall.sql.gz .
gunzip -c zwdatebot-postgres_pg_dumpall.sql.gz | \
  docker exec -i zwdatebot-local-postgres psql -U zwdatebot postgres
docker exec zwdatebot-local-postgres psql -U zwdatebot -d postgres \
  -c "ALTER ROLE zwdatebot PASSWORD 'zwdatebot';"
```

The `ALTER ROLE` afterwards is required: the dump carries the *prod* password
for the `zwdatebot` role and overwrites the local one, which breaks the seed
script and every host connection on port 5434. (Restoring into an already-seeded
database also spews `already exists` errors — harmless, or start from a fresh
volume with `down -v` first.)

Tear down: `docker compose -f deploy/compose.local.yml down` (`-v` to drop the
data volume too).

## Testing the SHV schedule sync locally

The sync derives its team id from the team's **website setting** - point it at a
matchcenter team URL (admin panel → ⚙️ Setup → 🌐 Website), e.g.
`https://www.handball.ch/de/matchcenter/teams/41317`, or via SQL:

```bash
docker exec -i zwdatebot-local-postgres psql -U zwdatebot -d zwdatebot -c \
  "INSERT INTO settings (id, team_id, website)
   SELECT 'config', id, 'https://www.handball.ch/de/matchcenter/teams/41317' FROM teams LIMIT 1
   ON CONFLICT (team_id, id) DO UPDATE SET website = EXCLUDED.website;"
```

No website = the team is skipped; a non-matchcenter website alerts the
maintainer (with a button to disable the sync for that team,
`settings.shv_sync_disabled`).

Then trigger one sync run against the live API without waiting for the daily job:

```bash
venv/bin/python -c "
import sys, asyncio; sys.path.insert(0, 'src')
from Utils.ApiConfig import ApiConfig
from data.DataAccess import DataAccess
from data.TenantContext import team_context
from features.shvsync import ShvApiClient, GameSyncPlanner

data_access = DataAccess(ApiConfig())
team = data_access.get_all_teams()[0]
with team_context(team.doc_id):
    shv_games = asyncio.run(ShvApiClient.fetch_games(
        ShvApiClient.parse_team_id(data_access.get_website())))
    plan = GameSyncPlanner.plan([g for g in shv_games if not g.is_played],
                                data_access.get_ordered_games())
    for field in ('auto_updates', 'adopt_questions', 'new_games', 'vanished', 'manual_leftovers'):
        print(field + ':', *getattr(plan, field), sep='\n  ')
"
```

That prints the plan without writing; to run the real thing (auto-updates applied,
admin questions with buttons in your DM), run the bot (`python src/main.py`) and
temporarily move the `shv_sync_service` job in `main.py` to
`job_queue.run_once(shv_sync_service.sync_all_teams, 5)`. You must be an admin of
the local team to receive and answer the questions.
