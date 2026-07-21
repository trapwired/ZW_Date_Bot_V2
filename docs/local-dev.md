# Local dev run (Postgres backend)

Run the whole bot locally against test data — confirm before a bigger merge
that everything still works, or try new features. Fully offline from prod.

## One-time setup

1. Create `secrets-local/` in the repo root (gitignored) with two files:
   - `api_config.ini` — copy `secrets/example_api_config.ini`, then set:
     ```ini
     [Telegram]
     api_token = <your DEV bot token from BotFather>

     [Database]
     backend = postgres
     dsn = postgresql://zwdatebot:zwdatebot@postgres:5432/zwdatebot
     ```
     (chat ids → your own Telegram id, like the example.)
   - the Firebase service-account JSON named in the config — only read while
     `backend = firestore`; keep the dev copy or an empty `{}` after Stage B.

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
```

Tear down: `docker compose -f deploy/compose.local.yml down` (`-v` to drop the
data volume too).
