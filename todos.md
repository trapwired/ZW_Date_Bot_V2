# ToDos — what we could do next

The architecture refactor is complete (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).
Everything below is optional follow-up work, grouped by size. Each item notes where to
start and a rough effort (S / M / L). Pick top-down within a group.

## Features (M)

- [ ] **Admin `/announce` broadcast** ("what's new" to admins/players).
  - Reuse the existing fan-out (`notify_all_players` / `TelegramService`); add a
    shared `NotificationService.broadcast(role_set, message)` the scheduling loops
    can use too.
  - Its own vertical slice; prefer an admin `/announce` command over a hardcoded
    deploy-time changelog script.
- [ ] **Per-user language switch (i18n).**
  - A `language` field on the user (`UsersToState` / `TelegramUser`); resolve it once
    per update (like the planned tenant context), don't thread it through every call.
  - The message/label strings live in `Format` / `PrintUtils` / `CommandDescriptions`
    — that layer becomes the single translation seam (keys → localized text).
  - Decide the string-catalog format + fallback language; `MessageType` is the
    natural key set.
- [ ] **Trigger: warn trainers when both keepers said no on a game.**
  - The stub comment already sits in `TriggerService.initialize_triggers`; the trigger
    itself is the easy part (pre_condition NO + GAME, condition via a domain predicate
    in `GameRules`, same shape as the low-availability one).
  - Needs a keeper designation first: `Role` is the single access-role enum
    (PLAYER/ADMIN/…), so keeper is an orthogonal *position* attribute on the player
    (e.g. `position` field on `TelegramUser`), not a new `Role` value.
  - Admins assign it via a flow analogous to `/assign_roles` (reuse that slice's
    pattern in `features/roles/`).

## Bigger bets (L)

- [ ] **Multi-team tenancy** — the flagship feature. Approach decided in
  [ADR 0001](docs/adr/0001-multi-team-tenancy.md): scope at the data boundary off an
  ambient tenant context; one Telegram user ↔ one team.
  - Onboarding: add admins on start, edit admins, set team name.
  - Data layer is the heavy lift (team-partitioned collections / a `teamId` filter on
    every read+write); `SchedulingService`'s global loops become per-team.

## Optional / nice-to-have

*(nothing right now)*
