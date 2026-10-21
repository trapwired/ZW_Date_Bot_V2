# Plan: personal calendar feed («Kalender-Abo») for ZW Date Bot

**Status:** implemented on branch `feat/calendar-feed`, 2026-10-21; hand-offs + device test
open (§11, §12). This file doubles as the handover. **Pattern source:** JugiBot
`~/dev/JugiBot/docs/CALENDAR_FEED_HANDOVER.md` (sections referenced as «handover §n»).
**Decided 21.10. with Domi:** hostname `zwbot.fluffyoctopus.ch`, ✅/❓ title prefix,
window = current season incl. past, entry = events-menu row + `/calendar`.
**Hosting:** Option A, in the bot process (§4, decided 21.10.).

## 1. What the user gets

- In the events list a row «📆 Kalender abonnieren» and the command `/calendar`. The bot
  answers in the private chat with a personal `https://zwbot.fluffyoctopus.ch/cal/<token>.ics`
  (tap-to-copy), per-platform steps, and a «🔄 Neuer Link» button. A new link kills the old one.
- The calendar app polls the URL. It shows the team's games, trainings and timekeepings of
  the current season (1 July → …) that the user has **not** declined. Title prefix
  **✅** = answered yes, **❓** = unsure or not answered. Declined → absent; answer changes
  → fixed on the next poll (hours; Google 12–24 h, not controllable).
- Spectators: games + trainings, no prefix (they cannot answer). Retired: like players.
  The gate is the events menu's `Audience.EVERYONE`: member roles PLAYER / SPECTATOR / RETIRED,
  plus any admin regardless of role (an inactive or rejected admin keeps the feed and the menu
  row, exactly like the events menu). Other inactive / rejected members, and teamless or removed
  members: the link answers `404`.
- The per-event «📆» download stays; it gets the same stable `UID` as the feed entry so a
  downloaded event and the subscribed one coincide (handover §6).

## 2. Decisions and why

| Decision | Why |
|---|---|
| Hand-rolled ICS renderer (~40 lines, port of handover §8), `ics` lib **not** used for the feed | Probe of `ics` 0.7.3 on Py 3.13: no line folding, `METHOD` after the events, no `DTSTAMP`, events in a `set` (unstable order), `FutureWarning` per alarm, no trailing CRLF. Post-processing would be as much code as rendering |
| Per-event download keeps `ics`, only gains `uid=` | Don't touch unrelated code; the drift risk is the title text, solved by one shared `event_summary()` |
| Link issued in Telegram, no `POST /issue` | Telegram identity *is* the login. The raw token lands in the DM history (delta to JugiBot, where it exists only in one response) → rotation is the remedy, the DM says so |
| `calendar_tokens` is a **global** table (user-bound), team resolved on every fetch | A user has one team (ADR 0001) but may change it; the feed follows the user. Removing the user purges the row |
| Token: 40 chars `secrets.token_urlsafe(30)`, store `sha256` hex, lookup by hash | Handover §4: 240 bit → no lockout needed, DB copy can't fetch a calendar |
| Feature dormant until `[Calendar] public_origin` is set | Code can ship and deploy before DNS/Caddy exist (same «deploy dark» pattern as Stage B) |
| DB calls on the HTTP path via `asyncio.to_thread` | `PostgresRepository` is sync (psycopg pool max 4); a slow query must not freeze Telegram handling on the shared loop |

## 3. Architecture

```
src/domain/EventVisibility.py      visible_event_types(role): THE «who sees which event types» rule
src/domain/calendar/               pure: no Telegram, no SQL
  Tokens.py                        mint_token (token_urlsafe(30)), hash_token (sha256 hex), token_from_feed_file_name
  EventSummary.py                  event_summary(type, event, team_name): the title, shared with the per-event download
  CalendarFeed.py                  build_feed_entries(events_by_type, attendances, role, team_name) → FeedEntry list:
                                   visibility, include/mark per attendance, sorted
  Ics.py                           render_calendar(entries, calendar_name, now), event_uid(doc_id):
                                   RFC 5545 escape, fold by octets, CRLF, UTC stamps
src/domain/entities/CalendarToken.py   entity: token_hash, user_id, created_at, last_used_at (repr omits the hash)
src/features/calendarfeed/         the slice
  CalendarFeedService.py           CalendarFeedConfig; issue_link(telegram_id), link_status(telegram_id), render_feed(file_name)
  CalendarFeedReplies.py           send_link_overview: the DM shared by the events-row tap and /calendar
  CalendarFeedMenu.py              CAL# callback codec (S = show/issue, R = rotate), entry row, link / «new link» markups
  CalendarFeedCallbackNode.py      CAL# taps → send_link_overview (first tap issues; later taps show status + button)
  FeedRoutes.py                    aiohttp routes: GET /cal/{file}, GET /healthz
src/framework/HttpServer.py        feature-agnostic aiohttp AppRunner start/stop
src/data/…                         Repository ABC + Postgres + InMemory: calendar-token methods, get_events_since (§8)
```

**Fetch path:** Caddy → aiohttp → `FeedRoutes` → `CalendarFeedService.render_feed`:
hash → token row (`find_calendar_token_by_hash`) → `get_user_by_doc_id` +
`get_user_state_for_user` (global tables) → `team_context(team_id)` +
`language_context(user_to_state.language or team.language)` → events since season start
(only the role's visible types) + `get_all_event_attendances(user)` →
`build_feed_entries(...)` → `render_calendar(...)` → `200 text/calendar`.
Unknown / rotated / malformed file name, or a user the bot no longer lists events for
(role not in `Audience.EVERYONE`, no team) → the same `404 text/plain` with one sentence.

**Authorization reuse (the one refactor, done):** «which event types does a role see» lived
in `EventsView._upcoming_by_type` (spectator: no timekeeping) — a view. The feed is a
second reader, so the rule moved to `domain/EventVisibility.py` and `EventsView` calls it.
`build_feed_entries` applies the same rule itself (it iterates `visible_event_types(role)`
and ignores any other type in its input): enforced at the source, not at the call site, so
no caller can leak a spectator's timekeeping. The service still queries only the visible
types, purely to save reads. Handover §8: the feed must call the *same* «who sees what»
as the list, never a copy.

## 4. Hosting: Option A (decided 21.10.)

**A, in the bot process.** Deciding argument: one deployment unit to run, deploy and watch,
and the slice is the same either way — B adds a second process and composition root, not a
second repo or image. Known cost of A: the public, unauthenticated HTTP ingress shares the
bot's loop, connection pool and process lifetime, so a feed bug or abusive traffic can degrade
or kill the Telegram side. Mitigations: `to_thread` for DB calls, strict `404`s, no per-fetch
alerts, handlers that do nothing but render. **Flip trigger to B:** not load (a handful of
polls per day) but blast radius — the first time the feed takes the bot down, or when the
bot's uptime is worth one more compose service. The flip is one file (§3).

| | A: in the bot process (chosen) | B: second container (later) |
|---|---|---|
| Server | `HttpServer.start` in PTB `post_init`, `stop` in `post_shutdown`. Verified for PTB 22: both run on `run_polling`'s loop, `AppRunner` installs no signal handlers, `close_loop` runs after `post_shutdown` | `src/feed_main.py`: builds `DataAccess` + `CalendarFeedService`, runs aiohttp alone. Same image, `CMD` override |
| Compose | bot service joins `web` (external) network, no `ports:` | new service `zwdatebot-feed`, networks `web` + `db`; bot service untouched |
| Caddy | `reverse_proxy zwdatebot:8080` | `reverse_proxy zwdatebot-feed:8080` |
| Liveness | existing healthchecks.io ping covers it | own signal needed (`/healthz` + uptime check, or a second ping) |
| Touches | `main.py`, compose, requirements | new entrypoint, compose, requirements, second composition root |

Both use the same slice; only the composition root differs, so flipping later is one file.

## 5. Data model

```waymark
/// One live calendar link per user. Global table (not team-scoped): the user's team is
/// resolved on every fetch. Only server code reads or writes it.
// Postgres table calendar_tokens; columns snake_case
type CalendarToken
    Id: string                /// uuid text PK, like every table
    TokenHash: string(64)     /// @format ^[a-f0-9]{64}$ — sha256 hex of the raw token; unique
    UserId: string            /// → users.id; unique → one link per user; purged with the user
    CreatedAt: datetime
    LastUsedAt: datetime?     /// stamped on every successful fetch, in try/except; null until then
```

```waymark
/// GET /cal/<token>.ics — 200 body, text/calendar (RFC 5545), one VCALENDAR
Version: "2.0"
ProdId: "-//ZW Date Bot//Kalender-Abo//DE"
CalScale: "GREGORIAN"
Method: "PUBLISH"
XWrCalName: string           /// "<team name>" — the calendar's name in the client
RefreshInterval: "PT6H"      /// REFRESH-INTERVAL;VALUE=DURATION — hint only
XPublishedTtl: "PT6H"
Events: list(0..)            /// one VEVENT per visible, not-declined event, sorted by start
    Uid: string              /// "<event doc_id>@zw-date-bot" — same in the per-event download; fixed forever (see below)
    DtStamp: datetime        /// UTC, time of this fetch
    DtStart: datetime        /// UTC (…Z), from event.timestamp (Zurich-aware → UTC)
    DtEnd: datetime          /// start + 90 min — the per-event download's constant, shared
    Summary: string          /// "✅ " | "❓ " | "" + event_summary(event, team) in the user's language
    Status: "CONFIRMED" | "TENTATIVE"   /// yes → CONFIRMED, else TENTATIVE (ignored by Apple/Google, cheap)
    Location?: string        /// left out when empty
    Description?: string     /// "Your answer: <emoji> <Yes|Unsure>" in the member's language; spectator: none
```

- **UID** is `<doc_id>@zw-date-bot`: a stable identifier, not a hostname. Calendar apps key
  events on it, so changing it later would duplicate every subscriber's events — it is
  fixed now (`Ics.UID_DOMAIN`). The per-event download uses the same `event_uid()`.
- **DESCRIPTION** carries only the member's own answer. `No` never appears (declined events
  are absent) and an unanswered event reads like `Unsure`, the bot's convention. No
  timekeeping «n Personen» line: the feed carries no head counts.
- **X-WR-CALNAME** is the team name. Response headers and the `404` body: §6.
- No `URL` (there is no web UI), no `VALARM` (subscribers set their own alerts; keeps the feed
  quiet). Event order and property order fixed → stable diffs in tests.

## 6. Feed rules (each one a unit test)

| Rule | Detail |
|---|---|
| Visible types | `visible_event_types(role)` (`domain/EventVisibility.py`), applied inside `build_feed_entries`: PLAYER/RETIRED/admin → all three; SPECTATOR → game + training |
| Include | attendance ≠ NO. No row = UNSURE (the bot's convention, `DataAccess.get_attendance`) |
| Mark | YES → ✅ + CONFIRMED; UNSURE/none → ❓ + TENTATIVE; SPECTATOR → no prefix, CONFIRMED |
| Window | `get_current_season_dates()[0]` (`domain/Season.py`, naive → made Zurich-aware by the service) ≤ timestamp. New repo query `get_events_since(table, since)` — **tz-aware** `since`, `DataAccess` raises on a naive one (TZ-frame gotcha; `get_future_events` compares a naive `datetime.now()`) |
| Times | UTC `Z`, no VTIMEZONE; single-day events, so no DST edge (handover §6) |
| Text | CRLF after every line incl. the last; fold > 75 octets (count UTF-8 bytes, never split a char); escape `\` `;` `,` newline in TEXT values |
| Reset | an event moved > 2 h resets answers to UNSURE (`AttendanceResetPolicy`) → ✅ flips to ❓ on the next poll. Correct: the user must re-answer |
| Deleted event | just absent → client removes it |
| 404 | unknown, rotated, malformed (`^[A-Za-z0-9_-]{40}\.ics$`), user without team/role → identical `404`, `text/plain; charset=utf-8`, `Cache-Control: no-store`, one bilingual DE/EN sentence («Dieser Kalender-Link gilt nicht mehr. Im Bot unter Termine → 📆 gibt es einen neuen. / This calendar link is no longer valid; get a new one in the bot under Events → 📆.»); bilingual because an unknown link has no user, hence no language |
| 200 headers | `Content-Type: text/calendar; charset=utf-8`, `Cache-Control: no-cache`, `Content-Disposition: inline; filename="zw-date-bot.ics"` |
| Errors | exception on the fetch path → `500`, logged at ERROR with traceback, **no** maintainer Telegram alert per fetch (a broken feed would spam every poll); the heartbeat/uptime signal is the alert |
| Side effects | `last_used_at` stamp in try/except — never breaks the feed |
| Logging | `HttpServer` sets the aiohttp access log to `'%a %s %b %Tf'` (client, status, bytes, seconds) — deliberately **no request line**, so a token in the path never reaches the container log. Caddy's access log is the one place a token still lands (§8) |

## 7. Bot UX

- **Entry row** appended by `EventsView` (`_member_entry_rows`, above the language row):
  `📆 Kalender abonnieren` → callback `CAL#S`. Shown on an empty events list too (a new
  member's first screen; the subscription fills up on its own). Own prefix `CAL`, routed in
  `NodeHandler.get_callback_node`; audience `EVERYONE` (same as the events node). Absent while
  the feature is off.
- **`/calendar`**: `MENU_COMMANDS` + `CommandDescriptions` + transition on `DefaultNode`
  with `in_keyboard=False` (like `/privacy`). In a group chat: silently dropped by
  `NodeHandler`, like `/help` — no reply, so a link can never land in a group. Row and command
  share one reply (`send_link_overview`).
- **First tap / no link yet:** issue, then DM (localized, 4 catalogs):
  1. the link in `<code>…</code>` (tap-to-copy),
  2. iPhone: Kalender-App › Kalender › Kalender hinzufügen › Abonnement-Kalender › Link einfügen,
  3. Android: Google Kalender am Computer › Weitere Kalender + › Per URL; plus an inline
     button «In Google Kalender öffnen» → `https://www.google.com/calendar/render?cid=<percent-encoded webcal://zwbot.fluffyoctopus.ch/cal/<token>.ics>`
     (https, so Telegram accepts it; undocumented Google link, verify on first test — §12),
  4. «Änderungen kommen mit Verzögerung (Stunden)», «Der Link ist persönlich — wer ihn hat,
     sieht deinen Kalender. 🔄 erzeugt einen neuen, der alte stirbt sofort.»
- **Later taps (second tap on):** status instead of a new link: «Du hast bereits einen
  Kalender-Link (erstellt am dd.mm.yyyy, zuletzt abgerufen: dd.mm.yyyy / noch nie).» + button
  «🔄 Neuer Link» (`CAL#R`) → rotate, send the DM above. The bot cannot show the current
  link again (hash only) — the text says so.
- `webcal://` is unusable in Telegram (Bot API rejects it in buttons/entities, clients don't
  linkify it) — hence tap-to-copy + steps. Optional later: an https landing page per token
  with a `webcal:` link for iPhone, if the steps prove too clumsy.

## 8. Touchpoints checklist (wire-up all)

Data
- [x] `src/data/schema.sql`: `calendar_tokens` (unique on `token_hash` and `user_id`)
- [x] `Enums/Table.py` + `data/Tables.py` (`GLOBAL_TABLES`, import-time assertion) + `secrets/example_api_config.ini` `[Tables] CALENDAR_TOKENS_TABLE`
  — the deploy-order trap is gone: that key is read **only by the in-memory test backend**
  (`Tables(api_config)`); `PostgresRepository` hardcodes its table names (`TABLE_SPECS`), and
  `initialize_tables` reads the key with `default='calendar_tokens'` anyway. The server's
  hand-edited `api_config.ini` therefore needs only the `[Calendar]` section (below).
- [x] `Repository` ABC: `replace_calendar_token(user_id, token_hash, created_at)` (atomic: one row
  per user, `last_used_at` restarts), `get_calendar_token_by_user`, `get_calendar_token_by_hash`,
  `touch_calendar_token`, `delete_calendar_token(user_id)`, `get_events_since(table, since)` →
  `PostgresRepository`, `InMemoryRepository` (`StubRepository` follows the ABC), `DataAccess`
  wrappers (`replace_calendar_token`, `get_calendar_token`, `find_calendar_token_by_hash`,
  `touch_calendar_token`, `delete_calendar_token`, `get_events_since`),
  `tests/contract/test_repository_contract.py` (runs on both backends)
- [x] User purge deletes the token on both backends: `PostgresRepository.delete_user_data` includes
  `calendar_tokens` in its transaction (`DataAccess.delete_user_data` ← `RoleService.remove_user`)

Domain + slice
- [x] `domain/calendar/{Tokens,EventSummary,CalendarFeed,Ics}.py`, entity `domain/entities/CalendarToken.py`, `domain/EventVisibility.py` (`visible_event_types(role)`, used by `EventsView` and `build_feed_entries`)
- [x] `features/calendarfeed/*`; `IcsService.get_ics` gets `uid=event_uid(doc_id)` and uses the shared `event_summary()` and `EVENT_DURATION`
- [x] `framework/HttpServer.py`; `main.py` `post_init`/`post_shutdown` wiring; `tests/conftest.py` `services` fixture mirrors it

Bot surface
- [x] `EventsView` entry row; `NodeHandler.get_callback_node` prefix; `NodeHandler.initialize_nodes` `/calendar`; `main.MENU_COMMANDS`; `framework/CommandDescriptions.py`
- [x] Locale catalogs de/gsw/fr/it (every new `t()` literal; `test_translation_catalogs` enforces) — also the `/privacy` text (one paragraph on the calendar link) and the welcome guide's «📆 Calendar» paragraph

Config + infra
- [x] `[Calendar] public_origin` (empty = feature off: no row, `/calendar` says «nicht eingerichtet», no HTTP server), `http_port` (default 8080); example config done. **Open:** server file (hand-off, `deploy/VPS_HANDOFF.md` §3)
- [x] `requirements.txt`: `aiohttp` (pinned, with its dependencies)
- [x] `Dockerfile` comment + `EXPOSE 8080` and `Heartbeat.py` docstring («no HTTP endpoint exists» is gone)
- [x] `deploy/compose.yml`: `networks: web: external: true` + `networks: [default, db, web]` on the bot service; repo copy synced with the server's `db` network. **Open:** the server copy is edited by hand (pull-based deploy, `deploy/VPS_HANDOFF.md` §2)
- [x] `deploy/compose.local.yml`: `ports: ["127.0.0.1:8080:8080"]` on the bot service; `docs/local-dev.md`: a `curl http://127.0.0.1:8080/cal/x.ics` step
- [ ] DNS (Domi): `A zwbot.fluffyoctopus.ch → 179.237.110.135` at the fluffyoctopus.ch registrar; must resolve before Caddy issues the cert
- [ ] Caddy (DomiCloud chat, via a hand-off file like `~/dev/hoisite/host/VPS_HANDOFF.md`):
  ```
  zwbot.fluffyoctopus.ch {
      import sec_headers
      import accesslog
      reverse_proxy zwdatebot:8080
  }
  ```
  The token sits in the path → it lands in Caddy's access log (accepted, handover §4; drop
  `import accesslog` for this host if you'd rather not). The bot's own aiohttp access log
  omits the request line (§6), so only Caddy has it.
  Written up for the DomiCloud chat in `deploy/VPS_HANDOFF.md` §4 (not yet executed).
- [x] Docs: `docs/ARCHITECTURE.md` (HTTP ingress, new slice, the «no HTTP» assumption gone; also its stale ADR list), `README.md` features, this file → now the handover

## 9. Security model (delta to handover §4)

Same as JugiBot: link = credential, hash-only storage, one link per user, uniform `404`,
authorization re-evaluated on every fetch, purge with the user, no names in the feed
(the feed carries only event data — a missing event tells the link holder «declined»).
Deltas: issuance via Telegram identity (no session, no `POST`); the raw token persists in
the Telegram DM until rotated; no admin can list tokens (no UI, by design); the nightly
pg_dumpall carries the hashes (restore kills links issued after the backup → re-issue).
Rate limiting: none in the app; Caddy and the 240-bit token are enough (handover §4).
Tokens stay out of logs on the bot side: the aiohttp access log has no request line (§6) and
`CalendarToken.__repr__` leaves the hash out. `/privacy` discloses the stored hash, its
created / last-fetched timestamps, that the link stays in the private chat, that a new link
kills the old one, that whoever holds the link sees the calendar, and the purge with the member.

## 10. Tests

- **Unit, `domain/calendar`:** CRLF incl. last line, no bare `\n`; fold by octets (`ü` line);
  escaping round trip; UTC `Z` from a Zurich-aware timestamp; UID stable; ✅/❓/none per
  role × state; NO excluded; window boundary; sorted; empty feed is a valid VCALENDAR.
- **Contract (both backends):** token upsert replaces the old hash (one row), lookup by hash,
  touch stamps `last_used_at`, delete by user, `get_events_since` honours the boundary with a
  tz-aware `since`.
- **Characterization (NodeHandler, FakeBot):** row tap → DM with link + steps; second tap →
  status + button; 🔄 → new link, old hash gone; `/calendar` in DM, and in a group it is
  silently dropped (no reply, no link); spectator gets the row, inactive doesn't (an inactive admin does); purge removes
  the row; feature off → no row (also none on the empty list).
- **HTTP (aiohttp `TestClient`, pytest-asyncio auto):** `200` headers + body shape; the five
  `404` variants (unknown, rotated, too short, no `.ics`, `.ics.ics`); tenant + language context
  set per request; a raising repository → `500`, no Telegram alert.
- **Real devices (gate before announcing, still open):** iPhone subscribe via steps, Google «Per URL» and the
  render-link button; declined event disappears after a poll; ✅→❓ after a reset.

Implemented in `tests/unit/test_{calendar_feed,calendar_feed_service,calendar_tokens,ics_render,feed_routes,http_server}.py`,
`tests/characterization/test_calendar_feed.py`, and the calendar-token cases of
`tests/contract/test_repository_contract.py`.

## 11. Work breakdown and delegation

1. **PR 1 «calendar feed, dormant»** — **implemented** on `feat/calendar-feed`, 2026-10-21;
   merge + deploy pending (one PR; ~2 focused sessions)
   - Fable (orchestrator, critical path): extract `visible_event_types` from `EventsView`,
     `main.py`/composition-root wiring, final review.
   - Opus: `domain/calendar/*` + unit tests; `CalendarFeedService` + `FeedRoutes` + `HttpServer`
     + HTTP tests; `CalendarFeedCallbackNode` + characterization tests.
   - Sonnet: repository methods on all three implementations + contract tests; `Table`/`Tables`/
     config; locale catalogs + `CommandDescriptions`; compose/Dockerfile/Heartbeat/docs edits.
   Deploy: nothing visible in prod (feature off).
2. **Hand-offs, in parallel (pending; written up in `deploy/VPS_HANDOFF.md`):** DNS record (Domi); Caddy
   block + server `compose.yml` network (DomiCloud chat); server `api_config.ini` `[Calendar]`
   section only — no `[Tables]` key needed (§8) (Domi).
3. **Switch-on:** restart container → `curl -i https://zwbot.fluffyoctopus.ch/cal/x.ics` (expect 404
   sentence) → issue a link in the real bot → subscribe on iPhone + Google → tick §10 devices.
4. **Follow-ups (not now):** per-event download onto the hand-rolled renderer and drop `ics`;
   https landing page with `webcal:` for iPhone; prune links unused for a year.

## 12. Risks and open items

- Real-device behaviour untested (same gap JugiBot still has); Google's poll interval is
  12–24 h and ignores the TTL hints — the DM says so («a few hours, Google Calendar up to a day»).
- **Unverified until the device test:** Google's undocumented `render?cid=` subscribe link
  behind «In Google Kalender öffnen», and the iPhone / Google app-menu wording in the
  de / gsw / fr / it DMs (`Kalenderabonnement hinzufügen`, `Per URL`, …) — the English menu
  path is the catalog source; the translated menu names were not checked against localized apps.
- Public traffic now rides the bot's loop and its 4-connection pool (§4): `to_thread` + tiny
  load make it fine, but a bug in the feed can take the bot down with it — that is the flip trigger.
- `DTSTAMP` = fetch time means every poll looks «changed» to the client; harmless (JugiBot same).
- Callback budget: `CAL#S` / `CAL#R` are far under 64 bytes.
- Team switch: the token follows the user; the feed silently shows the new team.
