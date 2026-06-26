# ZW_Date_Bot_V2 — Architecture Refactor Plan

Scope chosen: **Full reslice (Phases 0–4)**, **characterization tests first**.
Secrets confirmed dummy/safe — no secret remediation in this plan.

Status: PLAN ONLY. No code changed yet.

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
  new slice, not before.
</content>
