# ZW_Date_Bot_V2 — Architecture Refactor Plan

Scope chosen: **Full reslice (Phases 0–4)**, **characterization tests first**.
Secrets confirmed dummy/safe — no secret remediation in this plan.

## CURRENT STATUS (pick up here)

As of 2026-06-30 (`main` @ PR #12 merged):

- **Phases 0, 1, 2a, 2b-i…2b-iv: DONE.** Every *feature* node is
  `data_access`-free; all data access goes node → service → `DataAccess`. The
  pass-through services are right-sized: `StatisticsService` + `UserStateService`
  kept, `AdminService` inlined into `UserStateService` and deleted. 65 tests green
  (`./venv/bin/python -m pytest -q`).
- **One accepted exception** to "no `data_access` in `Nodes/`": the base
  `Node.get_commands_for_buttons` button-render reads (`Node.py:159-160`) — resolved
  in Phase 4 when base infra moves to `platform/`.
- **Tenancy decision recorded:** `docs/adr/0001-multi-team-tenancy.md` (one Telegram
  user ↔ one team; scope at the data boundary). Implementation is post-reslice.

**NEXT TASK → Phase 3** (collapse the 31→~12 `UserState` explosion). Then Phase 4
(physical reslice), Phase 6 (diagram), Phase 7 (comment cleanup). Each increment:
branch off `main`, pin the flow first where behavior is touched, one reviewable PR.

Convention this far: one vertical/concern per PR; `do_checks` runs at
`NodeHandler` construction so wiring errors fail the whole suite; commit trailer
`Co-Authored-By: Claude Opus 4.8 (1M context)`.

---

## Why we are doing this

Today the code is organized **by technical layer** (`Nodes/ Services/ Data/ Utils/ …`).
A single user-facing capability (e.g. "edit a game's opponent") is smeared across
7 files in 7 folders. Three event types (Game / Training / Timekeeping) are
implemented by **copy-paste** rather than polymorphism. The wizard steps of
"add an event" are modeled as **31 first-class states** in `UserState` instead of
as context. Business rules (e.g. the 2h-shift attendance reset) live **inside view
nodes**.

Target: **vertical slices** (folder per feature), **thin nodes** (parse → call
service → render), **domain logic in a domain layer**, event type as **data not
code paths**, and the wizard step held in **context (TempData)** so `UserState`
shrinks from 31 → ~12.

The existing `Transition`/`EventTransition` state-machine core and the
`FirebaseRepository` data boundary are good and are **kept**.

---

## Target structure (end state)

```
src/
  platform/        # the framework — feature-agnostic
    NodeHandler.py
    Nodes/Node.py, CallbackNode.py
    Transitions/*
    Services/TelegramService.py        # message transport only
  domain/          # behavior + rules, no Telegram, no Firebase
    events/        # Event aggregate; Game/Training/Timekeeping as field configs
    policies/      # e.g. attendance_reset_on_large_time_shift
    parsing/       # datetime parse/validate (from UpdateEventUtils)
    callbacks/     # single callback codec (merges CallbackUtils + RoleAssignment)
  features/        # one slice per capability: node + callbacknode + feature service
    eventmgmt/     # admin add/update/delete events + the wizard
    attendance/    # edit attendance + ICS export
    stats/
    roles/
    website/
  data/            # DataAccess + FirebaseRepository (already clean — unchanged)
  Enums/           # shared enums (UserState shrunk)
```

---

## Phase 0 — Safety net (do first)

Goal: make every later phase verifiable. **No production behavior change.**

1. **Re-enable startup invariants.** Uncomment `self.do_checks(api_config)` in
   `NodeHandler.__init__` (`NodeHandler.py:107`). Fix whatever
   `check_all_user_states_have_node` / `check_all_commands_have_description`
   surface. Add a smoke test that constructs `NodeHandler` and asserts checks pass.
2. **Stand up a test harness.** `pytest`. Fake the Firestore client (in-memory
   dict-backed `FirebaseRepository` double) so flows run without network.
3. **Characterization tests** (pin current behavior, bugs included):
   - Add-event wizard, all 3 event types: timestamp → location → (opponent) → save.
   - Edit attendance callback (UNSURE/YES/NO) writes correct state.
   - Update event timestamp; assert the >2h reset-all-attendance side effect fires.
   - Stats overview / per-event rendering.
   - `/start` init flow: new user → INIT, password → DEFAULT.
   - Role assignment callback.

   These tests are the contract the refactor must preserve. Capture the **current
   behavior even where it's wrong**, then fix bugs as explicit, separate commits.

Exit criteria: green suite, `do_checks` on, CI-able locally.

### Phase 0 — STATUS: in progress

Done:
- `do_checks()` re-enabled (`NodeHandler.py`); passes (all 31 states have nodes,
  all described commands have descriptions).
- Test harness up: `pytest` + `pytest-asyncio`, config in `pytest.ini`
  (`pythonpath = src`, `asyncio_mode = auto`). Dev deps in `requirements-dev.txt`.
  Note: project pip is pinned to a private DG Azure feed; install test deps with
  `pip install --index-url https://pypi.org/simple/ -r requirements-dev.txt`.
- Doubles at the two external boundaries (`tests/doubles/`):
  - `FakeFirestoreClient` — in-memory Firestore client; real FirebaseRepository +
    DataAccess run on top. `FakeFieldFilter` patched in for the google FieldFilter.
  - `FakeBot` — records outbound sends/edits/deletes; real TelegramService runs on top.
- Characterization tests (run through the real `NodeHandler.handle_message`):
  - `test_init_flow.py` — /start as member → DEFAULT+welcome; non-member → REJECTED;
    rejected + correct password → DEFAULT.
  - `test_add_event_wizard.py` — full game wizard (nav + persist), training
    (no opponent step), timekeeping, and /cancel.
- 10 tests green.

Deferred to the phase that touches them (write the pin right before the change):
- Edit-attendance callback flow + update-event 2h-reset policy → write at the
  start of Phase 2 (that's the code those characterize).
- These need a callback-query Update factory + query.edit_message_text wired to
  FakeBot; build that helper when Phase 2 starts.

Run: `./venv/bin/python -m pytest -q`

---

## Phase 1 — Kill duplication (behavior-preserving)

4. **Collapse the add-event wizard into one parametrized flow.**
   `AddEventFieldsNode` has 3 near-identical handlers
   (`handle_game_flow` / `handle_training_flow` / `handle_timekeeping_flow`,
   `AddEventFieldsNode.py:86-231`). They differ only by **field list**:
   Game = [timestamp, location, opponent], Training/Timekeeping = [timestamp, location].
   Replace with a single data-driven loop over a per-event field list. ~145 → ~50 LOC.
5. **Fix the markup bug found during review.** `update_inline_message`
   (`AddEventFieldsNode.py:73,77`) hardcodes `UserState.ADMIN_ADD_GAME, Event.GAME`
   for *all* event types. Use `self.event_type` and the matching add-state.
   (Make this its own commit so the characterization test flips intentionally.)
6. **Merge the two callback codecs.** `CallbackUtils` and `RoleAssignment` are two
   hand-rolled delimiter codecs. Extract one `domain/callbacks` codec; both call sites use it.
7. **De-triplicate small siblings:** `AdminNode` `handle_*_statistics`
   (`AdminNode.py:28-53`), `PrintUtils.pretty_print` Game/Training/Timekeeping
   overloads (`PrintUtils.py:110-157`).

Exit criteria: suite still green, duplication gone, markup bug fixed.

### Phase 1 — STATUS: done (branch `phase-1-kill-duplication`)

- AddEventFieldsNode: 3 copy-pasted flow handlers → one data-driven flow over a
  per-event-type step list (`_ADD_STEPS`). ~145 LOC → ~50.
- Markup bug fixed: `update_inline_message` now encodes the node's own event type
  instead of hardcoding `ADMIN_ADD_GAME`/`Event.GAME`. New regression test
  `test_add_event_markup.py` pins correct per-type callback_data.
- AdminNode: 3 identical `handle_*_statistics` → thin wrappers over
  `_handle_event_statistics(event_type)`.
- PrintUtils: the per-event single-line + attendance renderers collapsed via
  multipledispatch tuple types `(Game, Training, TimekeepingEvent)` — 9 defs → 3.
- **Callback codec merge: NOT done, deliberately.** `CallbackUtils`
  (`UserState#Event#CallbackOption#doc_id`) and `RoleAssignment`
  (`ROLES#code#args`) share only the `#` delimiter — different schemas, arities,
  value types, and routing. Merging two separate callback channels would be a
  leaky abstraction over incidental duplication (WET-when-right). Left separate;
  the earlier "duplicate codec" finding was over-stated.
- 28 tests green.

---

## Phase 2 — Drain logic out of nodes

Goal: nodes become thin — parse intent, call a feature service, render. **No node
calls `DataAccess` directly** after this phase.

8. **Move parsing to `domain/parsing`.** `UpdateEventUtils.parse_datetime_string`
   (domain validation) → domain. Returns a result object, not a `str`-or-value
   union (kills the `type(x) is str` error-signalling smell).
9. **Move the 2h policy to `domain/policies`.** Today at
   `EditEventTimestampNode.py:78`. Name it for what it does, e.g.
   `large_time_shift_invalidates_attendance`. The node asks the policy; it doesn't
   own the rule.
10. **Introduce feature services** (`eventmgmt`, `attendance`, …) that own the
    orchestration nodes currently do (get → mutate entity → persist → notify).
    Nodes call `eventmgmt_service.save_event(...)` etc.
11. **Right-size the pass-through services.** `UserStateService` / `AdminService` /
    `StatisticsService` (16-line delegators) either gain real responsibility or are
    inlined. No empty ceremony.

Exit criteria: grep shows no `self.data_access.` inside `Nodes/`; suite green.

### Phase 2 — split into 2a (done) and 2b (todo)

The full "no node touches DataAccess" sweep is too large for one reviewable PR,
so Phase 2 is split.

**Phase 2a — domain extraction (done, branch `phase-2-drain-logic-from-nodes`):**
- New `src/domain/` package.
- `EventDateTimeParser.parse()` replaces `UpdateEventUtils.parse_datetime_string`.
  Returns a `ParsedDateTime` result (`.ok`/`.value`/`.error`) instead of the
  str-or-Timestamp union — callers branch on `.ok`, not `type(x) is str`.
  Old function + `split_multiple` deleted; callers (AddEventFieldsNode,
  EditEventTimestampNode, PrintUtils) migrated.
- `AttendanceResetPolicy.requires_attendance_reset(old, new)` extracts the 2h
  rule out of EditEventTimestampNode (was a bare `pd.Timedelta(hours=2)` check in
  the view).
- Tests: characterization pin for the >2h / <2h reset flow added first; unit pins
  for the parser (new API) and the policy. 32 green.

**Phase 2b — node-thinning sweep (incremental, one vertical per PR):**

Too large for one PR (57 `data_access` calls across 18 node files), so done
vertical-by-vertical. Each increment pins its flow first, then routes persistence
through a feature service.

- **2b-i — EventService (done, branch `phase-2b-thin-nodes`):** new
  `Services/EventService.py` owns the event-management data orchestration
  (drafts, event get/update/delete, attendance reset, recipient lookup).
  `finalize_draft` folds add-event + discard-draft into one call so a saved draft
  can't linger. Thinned the three **text-driven** event nodes —
  AddEventFieldsNode, EditEventTimestampNode, EditEventLocationOrOpponentNode —
  to zero `data_access`. Added a characterization pin for the location/opponent
  edit. 41 green.
- **2b-ii — callback event nodes (done, branch `phase-2b-ii-callback-event-nodes`):**
  Built the callback-query Update factory + `drive_callback` harness. Pinned the
  delete-event, add-cancel and add-save callback flows, then routed
  UpdateEventCallbackNode (reads + delete) and AddEventCallbackNode
  (draft get/discard) through EventService — both now zero `data_access`. Added
  `EventService.delete_event` (now has a caller). Deleted the dead
  `AddEventCallbackNode.notify_all_players` (no caller) and its orphaned imports.
  Eventmgmt vertical complete: 5 nodes `data_access`-free. 44 green.
- **2b-iii-a — attendance (done, branch `phase-2b-iii-feature-services`):**
  new `AttendanceService`; EditCallbackNode (player YES/NO/UNSURE + calendar)
  routed through it — zero `data_access`. Also finished the eventmgmt vertical:
  AdminAddNode's draft creation now uses `EventService.create_draft`. Added the
  callback-attendance + calendar-export pins. 7 nodes `data_access`-free. 48 green.
- **2b-iii-b — roles (done, branch `phase-2b-iii-b-roles`):** new `RoleService`;
  AssignRolesCallbackNode and AdminNode.handle_assign_roles routed through it.
  Deduped the role-counts dict (built in both). AssignRolesCallbackNode now zero
  `data_access`. 8 nodes `data_access`-free.
  Review follow-up: closed a pre-existing **callback authorization gap** — no
  callback node checked the caller's role, so a forwarded admin inline button
  let a non-admin run admin actions (role assign = privilege escalation; event
  delete = data loss). Added a cross-cutting seam: `CallbackNode.required_roles`
  (mirrors `Transition.allowed_roles`), enforced once in
  `NodeHandler.is_caller_allowed`. Admin callback nodes declare `RoleSet.ADMINS`.
  Also fixed a duplicate `case Event.GAME` in AddEventCallbackNode RESTART
  (timekeeping restart was unreachable). 52 green.
- **2b-iii-c — website (done, branch `phase-2b-iii-c-website`):** new
  `WebsiteService` owns the player-facing URL plus the admin update flow
  (commit/discard of the URL staged in `additional_info`, folded so a committed
  URL can't be re-applied). UpdateWebsiteCallbackNode, AdminNode.handle_update_website
  and DefaultNode.handle_website routed through it — all three now zero
  `data_access` for the website slice (the callback's redundant `get_user`
  re-render fetch dropped: the callback Update already carries the admin's chat).
  Added the website-flow pin (confirm yes/no, admin display, player button,
  unconfigured). 9 nodes `data_access`-free. Review follow-up: `commit_pending_url`
  now validates the staged value is an http(s) URL and refuses anything else
  (closes a pre-existing gap where an empty/malformed URL was stored and later
  crashed the player `/website` button render with a Telegram BadRequest);
  invalid input tells the admin and leaves the link unchanged. 60 green.
- **2b-iii-d — stats (done, branch `phase-2b-iii-d-stats`):** expanded the stub
  `StatisticsService` with the stats read surface (`get_player_reminder_metrics`,
  `get_attendance_statistics`, `get_event_attendance_summary` folding the always-paired
  `get_stats_event`+`get_names`, `reset_reminder_statistics`). Routed StatsNode (its
  event read goes through the existing `EventService.get_event`), AdminNode's two
  statistics handlers, and ResetStatisticsCallbackNode through the services — all
  three now zero `data_access`. AdminNode is now fully `data_access`-free. Wired
  StatisticsService through main.py / NodeHandler / the test fixture. Added the
  stats-flow pins (reset yes/no, reminder + event statistics render). 12 nodes
  `data_access`-free. 65 green.
- **2b-iii-e — base reads (done, branch `phase-2b-iii-e-base-node-reads`):**
  routed the leftover feature-node reads through services - InitNode (new-user
  registration → `UserStateService.register_user`), EditNode (event read →
  `EventService.get_event`; attendance + TKE yes-count → new
  `AttendanceService.get_attendance`/`yes_count`), UpdateNode (event read →
  `EventService.get_event`). RejectedNode's explicit `data_access.update` was a
  redundant write - the framework's post-transition `update_user_state` already
  persists the role change - so it was deleted, not routed. Init/Rejected stay
  covered by the existing `test_init_flow` pin; Edit/Update are pure read-routing
  swaps. 65 green.
  - **Deferred (decision): the base `Node.get_commands_for_buttons` reads**
    (`get_user` + `get_all_event_attendances` for button rendering) stay on
    `data_access`. They live in the shared base class every node extends, so
    routing them through a feature service would inject that service into ~25
    node constructions and invert the layering (base infra depending on a
    feature slice). Revisit in Phase 4 when base infra moves to `platform/`.
    This is the one accepted exception to the "no `data_access` in Nodes/" exit
    criterion.
- **2b-iv — right-size the pass-through services (done, branch
  `phase-2b-iv-right-size-services`).** Read each delegator + its call sites, then
  decided keep/inline per service:
  - `StatisticsService` — **kept.** Real surface (5 methods) with 4 distinct
    callers incl. `SchedulingService`; already right-sized after 2b-iii-d.
  - `UserStateService` — **kept.** The central user-state seam, injected into every
    node via the base `Node`; `update_user_state` folds the mutate-then-persist
    invariant. Inlining would revert the whole sweep — it earns its keep.
  - `AdminService` — **inlined + deleted.** Misnamed (held one user-lifecycle
    mutation, not "admin"), single method, single caller, and stored-but-unused in
    `NodeHandler` (dead). Its `set_user_inactive` (`get_user_state` + `add_role` +
    `update`) is the same shape `UserStateService` already owns, so it moved there;
    `TelegramService` now depends on `UserStateService`. Dropped the dead
    `admin_service` ctor param from `NodeHandler`; rewired `main.py` /
    `NodeHandler` / the test fixture. Pure consolidation, no behavior change.
    65 green.

---

## Phase 3 — Collapse the UserState explosion

Goal: `UserState` 31 → ~12. Wizard step lives in `TempData`, not the enum.

12. **Add a `step` field to `TempData`** (already the natural home — it persists the
    in-progress event and even has `get_finished_event()`). The wizard advances
    `temp_data.step` instead of switching `UserState`.
13. **Merge states:** `ADMIN_ADD_GAME_{TIMESTAMP,LOCATION,OPPONENT,FINISH}` →
    single `ADMIN_ADD_GAME`; same for TRAINING / TIMEKEEPING. Update `NodeHandler`
    wiring (the big `all_nodes_dict`) and the callback state maps in
    `AddEventCallbackNode` / `UpdateEventCallbackNode` accordingly.
14. Re-run characterization tests — externally observable behavior must be identical.

> DDD note: the wizard is now an aggregate that owns its own step/invariant
> ("save only when required fields valid"). The invariant is enforced in one place
> instead of across 4 states × 3 nodes.

Exit criteria: ~12 states, `do_checks` green, suite green.

---

## Phase 4 — Physically reslice into features

Mostly mechanical once 1–3 are done.

15. Create `platform/ domain/ features/ data/`. Move files. Fix imports.
16. Each feature folder owns its `Node`, `CallbackNode`, and feature service.
17. Update `main.py` composition root and any import paths
    (`.github/workflows/deploy.yml`, `runtime.txt` unaffected; check the
    `src`-relative imports still resolve).
18. Update `README.md` + the excalidraw `ArchitectureOverview` to the new layout.

Exit criteria: capability change touches one folder; suite green; bot boots.

---

## Phase 6 — Final architecture diagram (closing deliverable)

Once the reslice has settled, produce a single **Excalidraw** document that shows
how the whole bot works end-to-end — the artifact a new contributor reads first.

It should capture:
- **External boundaries:** Telegram (updates in / messages out) and Firestore.
- **Request path:** Update → NodeHandler routing (text node vs callback node) →
  slice service → domain → data → Firestore, and the response back out.
- **Slices** (`eventmgmt`, `attendance`, `stats`, `roles`, `website`) and the
  shared `platform` / `domain` / `data` layers.
- **The collapsed state machine** (post-Phase-3 ~12 states), superseding the old
  `StateMachine.excalidraw` / `NodesInheritance.excalidraw`.
- **Background jobs:** the APScheduler reminders/summaries off SchedulingService.

Save as `docs/ArchitectureOverview.excalidraw` (replacing the stale one; remove
`StateMachine.excalidraw` / `NodesInheritance.excalidraw` if fully superseded).
Can be authored via the Excalidraw MCP or hand-written `.excalidraw` JSON. Do this
LAST so the diagram reflects the final structure, not an intermediate one.

Exit criteria: diagram matches the shipped code; README links to it.

---

## Phase 7 — Comment cleanup pass (closing deliverable)

During the refactor, docstrings and comments accumulate **historical narration** —
"used to do inline against DataAccess", "replaces the old str-union", "extracted
in Phase 2", "moved here in 2b". That framing helps reviewers mid-migration but
is noise once it ships: a comment should describe what the class/function **does
now**, not what it used to be or which phase changed it.

Final sweep once the architecture has settled:
- Rewrite every docstring/comment to describe present behavior and intent only.
- Remove phase references, "previously/used to/replaces/migrated from" wording,
  and before/after comparisons.
- Keep genuinely useful *why* comments (invariants, gotchas, cross-module
  contracts) — the rule is "explain the non-obvious why", not "narrate history".

Do this LAST so comments reflect the final design, not an intermediate step.

Exit criteria: no comment references a refactor phase or prior implementation;
comments describe current behavior only.

---

## Sequencing rationale

Tests → dedup → drain logic → collapse states → reslice. Each phase de-risks the
next: tests make refactors safe; dedup shrinks the surface before moving it;
draining logic must precede reslicing so the right code lands in the right slice;
state collapse is safest once flows are already single-path.

## Out of scope (note for later)

- Observability: the catch-all `except Exception` in `NodeHandler`/`Node` only DMs
  the maintainer — no metric/alert. Worth a Phase 5.
- Trigger system is wired but underused (`TriggerService.initialize_triggers`
  has a commented stub) — revisit when a second trigger is needed.
- Multi-team support (`todos.md`) — large feature; do it *after* the reslice, as a
  new slice, not before. Approach decided in
  [ADR 0001](adr/0001-multi-team-tenancy.md): scope at the data boundary off an
  ambient tenant context; assume one Telegram user ↔ one team.
</content>
