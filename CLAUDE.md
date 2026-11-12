# CLAUDE.md

For anyone — human or agent — changing this repo: how to run the checks, how a change
reaches prod, the conventions, and traps that already cost time. Where a doc or the code
says more, it wins.

## Read first, in this order

1. `README.md` — what the bot does, the slice layout.
2. `docs/ARCHITECTURE.md` — request flow, principles, jobs, HTTP ingress, known-open items.
3. `docs/adr/` — 0001 tenancy, 0002 self-heal on read, 0003 team repartition, 0004 per-user
   language, 0005 admin flag.
4. `docs/local-dev.md` — local bot + Postgres stack, seed script, local SHV sync run.
5. `todos.md` — the backlog, with entry points.
6. As needed: `docs/CALENDAR_FEED_PLAN.md` (calendar feed), `docs/onboarding-guide.md`, and
   the header comments of `.github/workflows/deploy.yml` and `Dockerfile`.

## Run the tests

- Python 3.13 venv; install as the header of `requirements-dev.txt` says (the explicit
  public index matters when a user-level `pip.conf` points elsewhere).
- `cp secrets/example_api_config.ini secrets/api_config.ini` — the tests read that file.
- `python -m pytest -q`. When the result gates the next step, run it bare: `pytest | tail`
  hides the exit code.
- **The Postgres half:** `tests/contract/` runs the `Repository` contract against the
  in-memory double AND a real Postgres. Without one on `POSTGRES_TEST_DSN` (default: host
  port 5433) that half **skips** — "N skipped" locally means it did not run. The
  `docker run` line is in the docstring of `tests/contract/conftest.py`; CI starts the same
  database as a service, so parity is enforced there.

## How a change reaches prod

Every merge to `main` that touches more than Markdown is a prod deploy.
`.github/workflows/deploy.yml` is the only workflow:

- `test` runs on every PR against `main` and every push to `main`. Branch protection
  requires only `test`, not strict.
- On push: `test` → `still-main-head` → image build and push → trivy gate (a fixable
  CRITICAL blocks) → cosign signature → signed webhook; the server pulls the image. No SSH.
- `still-main-head` deploys only while the commit is still main's head: in a burst of
  merges the older runs end `deploy: skipped`. `workflow_dispatch` deploys only from `main`.
- Pushes that change only `**.md` or `.github/dependabot.yml` start no run — prod keeps
  the previous, content-identical image.
- `deploy/compose.yml` is NOT shipped: when it changes, the server copy is updated by hand
  (server work, below).

**Verify after a merge:** take the run whose `headSha` equals `git ls-remote origin main`,
wait with `gh run watch <id> --exit-status`, then read `gh run view <id> --json
conclusion,headSha,jobs` (a piped `watch` hides failures). Report "test + still-main-head +
deploy success" for that commit. A failed deploy alerts nobody; it shows only in Actions.

**Gate changes, before pushing:** trivy locally with `--severity CRITICAL --ignore-unfixed
--exit-code 1` on the local image (its first run can exit 1 while fetching the DB — rerun);
workflows with `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest`.

## PR conventions

- Branch from a freshly fetched `origin/main`; one concern per PR; tests green before push.
- Before merging, read the PR's commit list: GitHub "potential fix" auto-commits can change
  code silently.
- Merge = squash, branch deleted: `gh pr merge N --squash --delete-branch`. Stacked PRs
  retarget to `main` only when the parent branch is deleted; check
  `gh pr view <child> --json baseRefName` before merging the next one.

## Dependabot

Merge when the risk is small — "our code paths verified unaffected" counts, even when an
upstream consumer is still incompatible. Otherwise hold, with evidence and a one-line path
to go ahead.

- CI tests each PR alone: test several pip bumps **combined** in a scratch worktree of
  `origin/main` (pins edited, fresh venv, full suite), then merge one at a time.
- Consumers of a transitive pin: `pip show <pkg>` → `Required-by`, then grep `src`.
- Action bumps: the pinned SHA must equal the tag's commit.
- Two bumps on adjacent lines of one file conflict after the first squash: comment
  `@dependabot rebase` on the second, wait for `test`, merge. Then verify the deploy.

## Server work: not from this repo

Sessions in this repo do not SSH to the VPS. Server-side changes — server compose file,
server `api_config.ini`, reverse proxy, DNS, SQL on prod — are written up as a hand-off
(numbered steps, each naming who runs it, the target file, a check; a rollback at the end)
and run by the DomiCloud ops session or the owner, after the deploy they depend on. Never start a second process on the prod bot token:
Telegram allows one `getUpdates` poller per token; local dev uses its own bot.

## Intended behaviour that looks like a bug

- The spectator password is case-sensitive.
- Active players are `role == PLAYER` only: an admin who does not play gets no reminders and
  is absent from overviews, announce DMs and the trainer roster.
- The low-attendance warning fires when yes + unsure drop to `MAX_PLAYERS_PER_GAME` (9): a
  roster of 10 or fewer fires on the first NO. A RETIRED player's yes counts.
- Spectators do not see timekeepings (`domain/EventVisibility`).
- A button pressed while the bot restarts (every deploy) gets "Query is too old": the
  presser is told, the maintainer is not. A stale attendance tap is still saved; the card
  refresh and the triggers after it are lost.
- Season stats roll over on 1 July — empty stats in July are correct.
- SHV sync imports only the next `IMPORT_WINDOW_GAMES` (3) feed games; non-final declines
  are asked again after 14 days; adoption is capped at 30 days. SHV mints a new team id each
  season: the team's website URL must be replaced; the "empty upcoming feed" alert catches
  a stale one.
- Calendar feed choices (fixed event UID, no request line in the access log, `/calendar`
  dropped in groups) are decisions in `docs/CALENDAR_FEED_PLAN.md`.
- Admin panel action codes are never renumbered, so old buttons in chats keep working.

## Known pitfalls

**Callback data.** One button over 64 bytes of `callback_data` makes Telegram reject the
WHOLE markup — the menu just stops updating. Postgres ids are 36-char UUIDs, migrated rows
keep 20-char ids. Only the `ROLES#` codec enforces the budget (`RoleAssignment`); `EV#` and
`AP#` carry UUIDs unguarded. The in-memory double mints short ids, so no test catches an
overflow. Team stamping of admin buttons: `framework/TeamStamp.py`.

**Typed input.** A stale Save/delivery button pressed during ANOTHER typed-input flow would
commit that flow's staged value. The team-name, announce and rename commit handlers check
that the user's state is their own flow's — do the same in every new flow.

**Time.** CI and prod run UTC (no `TZ` set anywhere); the domain is Europe/Zurich. Take
"now" and "today" from `DateTimeUtils.get_local_now()` — in tests too; a naive
`datetime.now()` / `date.today()` follows the host clock. The suite passes under any host
clock: check a time change with `TZ=UTC` and `TZ=Asia/Tokyo`. `tests/helpers.host_clock_in`
moves the clock inside one test.

**Sending.** `TelegramService._send_message` swallows Forbidden (sets the user INACTIVE)
and "chat not found" and DMs the maintainer, so one dead chat cannot abort a loop.
`send_message_or_raise` raises; role-change notices must use it. Long HTML reports go
through `PrintUtils.split_pre_report`; HTML-escape team and player names.

**i18n.** Text formatted at import time or before translation freezes one language:
translate first, format at call time. `gsw` cannot be registered with `set_my_commands`.

**State.** `TeamService` caches teams for the process lifetime: restart the bot after
editing team rows by SQL. Self-heal on read (ADR 0002) writes nothing back: a query that
filters on a stored legacy value still finds old rows until a real migration runs.

**Dependencies.** Bot code uses pytz only. pandas up to 3.1.0 breaks on python-dateutil 3
zones (`AttributeError … 'total_seconds'`): never feed `dateutil.tz` zones into pandas.
`ics` serves only the per-event download; the feed has its own renderer. pytest ≥ 9.2:
`parametrize`'s `indirect` / `ids` / `scope` are keyword-only.

**Test harness.** Doubles sit only at storage (`tests/doubles/in_memory_repository.py`,
segregated by table name, so `[Tables]` names must be distinct — they matter only to the
tests) and Telegram (`fake_bot.py`). `TelegramService` checks `type(update) is Update`:
build real updates with `tests/helpers.py`; a `SimpleNamespace` silently disables
`assert_no_error_reported`. `NodeHandler.do_checks` fails the suite on wiring errors.

**Compose.** `deploy/compose.local.yml` carries `name: zwdatebot-local` — keep it: without
it compose names the project after the `deploy/` folder and `up` can remove another repo's
containers.
