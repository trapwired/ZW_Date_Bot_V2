# ToDos — what we could do next

The architecture refactor is complete (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).
Everything below is optional follow-up work, grouped by size. Each item notes where to
start and a rough effort (S / M / L). Pick top-down within a group.

## Quick wins (S)

- [ ] **`/help` lists AND explains every available option.**
  - `do_checks.check_all_commands_have_description` already fails the suite if a
    *described* command lacks a description; extend the guarantee so `/help` renders
    every active transition for the user's state + role, each with its explanation.
  - Single source of truth: `CommandDescriptions`; help should derive from the same
    transitions the keyboard does (`get_commands_for_help`) so they can't drift.

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
- [ ] **Redesign the menu / submenu experience for accessibility.**
  - The reply-keyboard layout is built in `TelegramService` (fixed per-screen layouts)
    + the state → commands rendering; rework it now that nodes live in feature slices.
  - Goals: fewer/clearer levels, consistent back/overview, discoverable actions.

## Bigger bets (L)

- [ ] **Multi-team tenancy** — the flagship feature. Approach decided in
  [ADR 0001](docs/adr/0001-multi-team-tenancy.md): scope at the data boundary off an
  ambient tenant context; one Telegram user ↔ one team.
  - Onboarding: add admins on start, edit admins, set team name.
  - Data layer is the heavy lift (team-partitioned collections / a `teamId` filter on
    every read+write); `SchedulingService`'s global loops become per-team.
  - **Fold in the base-node data read here:** `framework/Nodes/Node.get_commands_for_buttons`
    still reads `data_access` directly (`get_user`, `get_all_event_attendances`) — the one
    place a node touches data. It must become tenant-aware, so resolve it as part of this.

## Optional / nice-to-have

- [ ] **Deeper `UserState` collapse (23 → ~12).** Fold the per-type
  `ADMIN_ADD_*` / `STATS_*` / `EDIT_*` families into single states with the event type
  in context. Diminishing returns — those already share node classes, so it mostly
  trims the enum + wiring, not code duplication.
