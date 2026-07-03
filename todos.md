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

- [ ] **Invite deep-links for spectators (and maybe players).** Replace/augment the
  shared spectator password with admin-generated links (`t.me/<Bot>?start=<random
  token>`): unguessable, revocable, optionally one-time or expiring — removes the
  brute-force surface entirely. Telegram delivers the token as the `/start` payload,
  so the entry point is `InitNode.handle_start` (parse the payload before the
  membership gate); tokens live on the team doc or an `invites` subcollection; admin
  menu gets a "create invite link" action. The password flow + its throttle
  (`domain/SpectatorPasswordPolicy`) can stay as fallback or be retired then.

- [ ] **Live-test more group chats / teams.** Register additional real Telegram
  groups as teams (beyond Züri West + the scratch test group) and walk the full
  flow per team: `/register_team` → membership gate on `/start` → spectator
  password → events + attendance → scheduled reminders/summaries routing to the
  right group and trainers. Goal: confidence that team isolation and per-team
  routing hold with real chat ids, not just the fake-Firestore tests.

- [ ] **General onboarding material for new teams.** The new-member guide (PR4 of the
  tenancy work) covers players/spectators of an existing team; still open: guiding a
  fresh team admin end-to-end (add bot to group → /register_team → set spectator
  password → add first event → invite members), plus screenshots or a short video
  once the UI is stable. Entry point: `features/onboarding/WelcomeGuide.py` and
  `docs/onboarding-guide.md`.

## Advertising / adoption (non-code)

- [ ] **Promote the bot at different locations.** Once multi-team is live-verified,
  actively recruit teams. Candidate channels:
  - Own club first: other Züri West teams / other squads in the club.
  - League/association contacts: teams the club plays against (trainers already
    exchange schedules), regional handball/unihockey association newsletters.
  - Local sports venues / clubhouses (notice board, QR code to the bot).
  - Online: Telegram bot directories, team-sport subreddits/forums, a simple
    landing page (the website link the bot already serves) with a "get started"
    section.
  - Prerequisites before advertising: onboarding guide (PR4), invite deep-links or
    a polished password flow, and a support/contact path for new team admins.
