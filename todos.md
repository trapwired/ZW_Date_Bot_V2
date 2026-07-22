# ToDos — what we could do next

The architecture refactor is complete (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).
Everything below is optional follow-up work, grouped by size. Each item notes where to
start and a rough effort (S / M / L). Pick top-down within a group.

## Hosting / migration (time-bound — from the VPS migration, plan in the DomiCloud repo)

Bot runs containerized on the Infomaniak VPS against Postgres since 22.07.
(Stage A hosting 21.07., Stage B database 22.07.; Firestore frozen = rollback.)

- [ ] **B5 — Firebase decommission: delete the project (last step, Domi).** Done
      22.07.: final Firestore export (5774 docs incl. legacy collections) archived to
      kDrive `Backups/zw-date-bot-firestore-final/`; firebase strip PR (this branch);
      local-dev flow + restore drill run end-to-end. Remaining: delete the
      `zw-date-bot` Firebase project in the console (30-day recovery window applies)
      and a quick Telegram smoke test of the local dev bot.
- [ ] **~28.07. droplet decommission** (tracked in cado repo too): retires the whole
      DO box → then delete the `DROPLET_HOST`/`DROPLET_SSH_KEY` repo secrets here,
      and the throwaway test bot in BotFather can go anytime.

## Features (M)

- [ ] **Trigger: warn trainers when all keepers said no to a game.**
    - The stub comment already sits in `TriggerService.initialize_triggers`; the trigger
      itself is the easy part (pre_condition NO + GAME, condition via a domain predicate
      in `GameRules`, same shape as the low-availability one).
    - Needs a keeper designation first: keeper is an orthogonal *position* attribute
      on the player (e.g. `position` field on `TelegramUser`), not a new `Role` value —
      same orthogonal-attribute pattern as the `is_admin` flag (ADR 0005).
    - Admins assign it via a flow analogous to `/assign_roles` (reuse that slice's
      pattern in `features/roles/`).
    - Also needs a settable "which sport does this team play" entry per team (keeper
      only makes sense for some sports). Home: the admin flow, or a separate one-time
      SETUP flow that runs when the bot is first set up for a team.

## Optional / nice-to-have

- [ ] **Invite deep-links: follow-ups.** One-time spectator links shipped (admin
  panel 🔗 → `t.me/<Bot>?start=<token>`, token on the team doc, dies on redemption).
  Still open if ever needed: list/revoke outstanding tokens, expiry, player invites,
  and retiring the password flow + its throttle (`domain/SpectatorPasswordPolicy`)
  once links prove themselves.

- [ ] **Live-test the full multi-team flow (THE gate before advertising).** With a
  second account and the scratch test group, walk everything end-to-end with real
  chat ids: add bot to group (setup DM to the adder, group fallback link) → members
  `/start` → spectator password AND one-time invite link (second use rejected) →
  admin panel sections (password lands on Spectators overview, name/website on
  Setup) → trainer toggles → announce (both channels) → scheduled reminders/
  summaries routing → forwarded admin button pressed cross-team (refused) → remove
  bot from a fresh team (full rollback). Goal: team isolation + the new onboarding
  hold outside the fake-Firestore tests.

- [ ] **Onboarding screenshots / video.** The guided flows exist (teamless choice
  screen, add-bot-to-group setup trigger, admin setup DM); once the UI is stable,
  add annotated screenshots or a short video to `docs/onboarding-guide.md` and the
  future landing page.

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
    - Prerequisites before advertising: the live-test above and a support/contact
      path for new team admins (onboarding guide + invite links are done).

## Maybe

Fun/engagement ideas, not committed. Each is its own vertical slice under
`features/`; attendance + reminder stats already carry most of the data.

- [ ] **Roast-mode reminders 🔥 (S).** Escalating reminder personality: first polite,
  second sassy, third savage. Static line pool, per-team on/off toggle (team doc
  flag). Cheap, screenshot-worthy — free bot advertising.
