# ADR 0003 — Repartition existing single-team data with a one-off idempotent migration script

- **Status:** Accepted
- **Date:** 2026-07-03
- **Deciders:** Dominic Weibel

## Context

ADR 0001 chose **per-team subcollections** (`teams/{teamId}/<collection>`) as the
tenancy layout. The existing production data predates that decision: every domain
collection still lives in a **flat root collection** (`games`, `trainings`,
`game_attendance`, …). Before the tenant-scoped `FirebaseRepository` can serve
reads, that data has to physically move under a team document.

ADR 0002's **self-heal-on-read** strategy does not apply here. Self-healing works
when a persisted value can be *reinterpreted* at the deserialization boundary — a
legacy `state` int coerced to its surviving enum member. A repartition changes
where a document **lives**, not how it parses: a doc at `games/{id}` and the same
doc at `teams/{teamId}/games/{id}` are byte-identical, so there is no deserialization
seam that can relocate it. The tenant-scoped `_collection()` resolver reads
`teams/{teamId}/games` and simply finds nothing until the documents are actually
there. Relocation is a physical operation, so it needs a migration.

## Decision

A **one-off, idempotent migration script** (`scripts/migrate_to_multi_team.py`),
run once with the **bot stopped**.

- **Team document.** The script resolves the single existing team by
  `groupChatId` (seeded from `[Chat_Ids] GROUP_CHAT`), reusing it if present so a
  re-run does not create duplicates, otherwise creating it from config
  (`name`, `groupChatId`, `[Chats] SPECTATOR_PASSWORD`, `[Chat_Ids]
  TRAINERS_GAMES` / `TRAINERS_TRAINING`).
- **Domain collections.** The nine team-scoped collections are copied
  `flat/<name>/{id}` → `teams/{teamId}/<name>/{id}` with **doc ids preserved** —
  cross-references (`Attendance.eventId`, `PlayerMetric.userId`,
  `Attendance.userId`) are stored as doc ids, so preserving them keeps every
  reference valid without rewriting any field.
- **Identity stays global.** `users` is untouched. Each `users_to_state` doc is
  stamped with a `teamId` field, except records whose role is `INIT` (-1, not yet
  registered) or `REJECTED` (999), which are not bound to any team.
- **Idempotent.** Every write is a `set()`/`update()` to a deterministic target,
  so re-running overwrites identically and never duplicates.
- **Verification.** After copying, the script compares source vs. destination
  document counts per collection and checks the first document for exact
  dictionary equality; any mismatch prints a `FAIL` line and exits non-zero.
- **Flat collections are retained** as the rollback path and deleted **manually**
  later, once the new layout is trusted. The script never deletes them.

### Edge cases

- **A user switches teams:** a manual Firestore edit by the maintainer. ADR 0001's
  *one user belongs to exactly one team* stands; there is no self-service team
  switch.
- **Team deletion:** out of scope.
- **Two teams may not share a Telegram group chat** — `groupChatId` identifies the
  team on the group side.
- **Spectator passwords must be unique across teams** — the password is how a
  spectator selects which team to join, so a collision would be ambiguous.

## Consequences

**Positive**
- One storage layout everywhere: after the migration there is **no permanent legacy
  special case** in the `_collection()` resolver — it only ever resolves
  `teams/{teamId}/<name>`.
- Doc-id preservation means zero reference rewriting and a trivial equality check
  for verification.

**Negative / cost**
- An **ops step** is required, with a strict deploy order:
  1. **stop** the bot,
  2. **pull** the new revision,
  3. add `TEAMS_TABLE` (and the team-seed keys, if missing) to the secrets
     `api_config.ini`,
  4. **run** `./venv/bin/python scripts/migrate_to_multi_team.py`,
  5. **verify** the `OK <name>: n -> n` lines and a zero exit code,
  6. **start** the bot.
- A short **write-freeze window**: the bot is down for the duration of the copy, so
  no events/attendance are written mid-migration.

**Applicability**
- This is the counterpart to ADR 0002's caveat: a change with no safe read-time
  coercion — here, documents that must physically move — needs a real migration and
  its own ADR. This is that ADR.

## Related

- ADR 0001 — per-team subcollection tenancy layout this migrates onto.
- ADR 0002 — self-heal-on-read, the strategy that explicitly **cannot** cover a
  physical repartition.
- `scripts/migrate_to_multi_team.py` — the migration script this ADR governs.
