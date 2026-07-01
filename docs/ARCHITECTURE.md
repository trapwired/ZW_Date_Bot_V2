# ZW_Date_Bot_V2 — Architecture

A Telegram bot that manages a sports team's schedule (games, trainings, timekeeping
events) and tracks each player's attendance. This document describes how the code is
organized and why. The interactive diagram is linked from the [README](../README.md).

## Layout

The code is organized as **vertical slices** on a shared spine:

```
src/
  framework/   feature-agnostic runtime: NodeHandler, Node/CallbackNode, Transitions,
               TelegramService, UserStateService, TriggerService, SchedulingService,
               NodeUtils, CommandDescriptions
  features/    one folder per capability, each owning its Node(s) + Service:
               eventmgmt · attendance · stats · roles · website · onboarding · menu
  domain/      entities + business rules (policies, parsing) — no Telegram, no Firestore
  data/        DataAccess + FirebaseRepository (the Firestore boundary)
  Enums/  Utils/   shared cross-cutting code
```

A change to one capability should touch one `features/<slice>` folder, not ripple
across horizontal layers.

## How a request flows

1. A Telegram update reaches **`NodeHandler`**, which looks up the user's `UserState`
   and routes: plain text → a feature **Node**, an inline-button tap → a **CallbackNode**.
   Callback nodes are additionally role-gated (`CallbackNode.required_roles`).
2. The node parses the input and calls its slice **Service** for orchestration.
3. The service works through **`domain`** models and rules, and reads/writes via the
   **`data`** layer to **Firestore**.
4. The reply is rendered and sent back out through **`TelegramService`**.

Nodes stay thin (parse → call service → render); orchestration and data access live in
the services, not the view nodes.

## Design principles

- **Thin nodes, service-owned data access.** A feature node never touches `DataAccess`
  directly; it goes node → service → `DataAccess` → Firestore. This keeps the number
  of places that touch data small and auditable — the foundation the tenancy work
  builds on (see ADR 0001). The one exception is the base `Node.get_commands_for_buttons`
  button-render read (see Known-open items).
- **Domain logic in the domain layer.** Business rules (e.g. the ">2h event move
  invalidates attendance" policy, datetime parsing/validation) live in `domain/`, not
  inside view nodes.
- **Event type is data, not code paths.** Game / Training / Timekeeping are handled by
  one polymorphic flow parameterized by `Event`, not by three copy-pasted handlers.
- **Wizard/edit step lives in context, not the state machine.** The add-event wizard's
  current field is held in `TempData.step`; the update-event edit carries its field and
  event type in `UsersToState.additional_info`. `UserState` models *where the user is*,
  not *which form field is being collected* — so it stays small (currently 23 values)
  instead of one state per field × event type.
- **Startup invariants.** `NodeHandler.do_checks` runs at construction and asserts every
  `UserState` has a node and every described command has a description, so a wiring
  mistake fails the whole test suite immediately.

## Persistence & backward compatibility

Schema-affecting state changes **self-heal on read** rather than via bulk migration
scripts (see ADR 0002): `UserState._missing_` coerces removed legacy enum values to
their surviving state, and `TempData.from_dict` infers a missing `step` from the fields
already collected. A user mid-flow at deploy time is read back cleanly instead of
crashing.

## Background jobs

`SchedulingService` runs on APScheduler to send attendance reminders and trainer
summaries. It reads events via `data` and sends via `TelegramService`.

## Decisions (ADRs)

- [ADR 0001 — Multi-team tenancy](adr/0001-multi-team-tenancy.md): scope at the data
  boundary off an ambient tenant context; one Telegram user ↔ one team. Not yet
  implemented.
- [ADR 0002 — State migration strategy](adr/0002-state-migration-strategy.md):
  schema-affecting state changes self-heal on read, no bulk migration.

## Known-open items

- **Observability.** The catch-all `except Exception` in `NodeHandler` only DMs the
  maintainer — no metric or alert on failures. Worth adding structured logging + an
  alert, and distinguishing expected dead-letters from unexpected crashes.
- **Base-node data read.** `framework/Nodes/Node.get_commands_for_buttons` reads
  `data_access` directly (`get_user`, `get_all_event_attendances`) to render buttons —
  the one place a node still touches data. It must become tenant-aware; cleanest to
  resolve alongside the tenancy work (ADR 0001).
- **Trigger system** (`TriggerService.initialize_triggers`) is wired but underused —
  revisit when a second trigger is needed.
- **Unplaced shared code:** `Triggers/` (trigger domain objects) and root
  `OneTimeSetup.py` (a manual seeding script) don't yet have a settled home.

Longer-term product ideas (multi-team, admin broadcast, per-user language, menu
redesign, `/help` completeness) are tracked in [`todos.md`](../todos.md).
