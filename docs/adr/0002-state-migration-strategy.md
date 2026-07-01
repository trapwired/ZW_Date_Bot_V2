# ADR 0002 — Schema-affecting state changes self-heal on read (no bulk migration)

- **Status:** Accepted
- **Date:** 2026-07-01
- **Deciders:** Dominic Weibel
- **Context:** decided during the `UserState` collapse.

## Context

The refactor changes persisted shapes. Collapsing the add-event wizard deleted 10 `UserState` enum values
(the per-field add-event wizard states) and added a `TempData.step` field. Both the
`UserState` of a user and the in-progress `TempData` draft are persisted in Firestore,
so at deploy time there can be **live records carrying the old shape**:

- a user who was mid add-event wizard has a persisted `state` int (e.g. `104`,
  the old `ADMIN_ADD_GAME_LOCATION`) that no longer maps to any enum member;
- their draft has no `step` field, because it was written before the field existed.

`UsersToState.__init__` and `TempData.from_dict` both coerce persisted values back into
enums (`UserState(int(state))`). A now-unknown int raises `ValueError`, which would
crash the user's next interaction and leave them stuck.

Two strategies were considered:

1. **Bulk migration** — a one-time script run at deploy that rewrites every affected
   record (reset each user's `state` to `DEFAULT`, delete orphaned drafts) and sends
   every user a fresh keyboard so their client UI matches the new state.
2. **Self-healing on read** — the deserialization boundary tolerates and coerces the
   old shape, so records fix themselves the next time they are touched.

## Decision

**Self-healing on read.** Schema-affecting `UserState`/entity changes are absorbed at
the deserialization boundary rather than by a bulk migration script.

- `UserState._missing_` maps deleted legacy ints to their surviving parent state
  (the legacy add-wizard values → `ADMIN_ADD_GAME` / `_TRAINING` / `_TIMEKEEPING`).
  Genuinely unknown values still raise, so typos/corruption are not silently masked.
- `TempData.from_dict` infers `step` from which fields are already filled when the
  persisted draft has none, so an in-flight wizard resumes where it left off instead
  of restarting.

The two coercions align: a legacy state reads back as the parent, and the stepless
draft infers the matching step, so a mid-wizard user is fully restored with no manual
intervention.

### Why not the bulk migration

- **Zero ops step.** No script to remember to run, no ordering coupling with the deploy.
- **No lost work.** In-flight wizards keep their progress; the reset approach would
  discard them.
- **No mass broadcast.** Resetting `state` server-side does not change the reply
  keyboard the user currently sees (Telegram keeps the last-sent keyboard until the
  next message), so the reset path would *also* require messaging every user. Self-
  healing needs neither.
- **Team scale.** A single-team bot has few concurrent users; the mid-migration window
  is tiny and the read-boundary guard covers even that.

## Consequences

**Positive**
- Deploys of state-shape changes need no data migration and no downtime.
- The guard is a single auditable seam per entity, unit-tested
  (`tests/unit/test_legacy_state_migration.py`).

**Negative / cost**
- Carries a small legacy-mapping table (`_LEGACY_ADD_STATES`) that is dead weight once
  no old records remain. Acceptable; remove in a later cleanup when confident, or leave.
- Self-healing hides the fact that legacy data existed — there is no report of how many
  records were coerced. Fine at this scale; revisit if a future change needs an audit.

**Applicability**
- This works because every removed value has a sensible surviving target and drafts are
  short-lived scratch state. A change with **no** safe coercion (e.g. dropping a field
  other code requires) would need a real migration and a new ADR.

## Related

- `docs/ARCHITECTURE.md` — the `UserState` collapse this covers.
- `src/Enums/UserState.py` (`_missing_`), `src/domain/entities/TempData.py`
  (`from_dict` / `infer_step`).
