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
               CommandDescriptions
  features/    one folder per capability, each owning its Node(s) + Service:
               events · adminpanel · eventmgmt · attendance · stats · roles · website
               · onboarding · menu
  domain/      entities + business rules (policies, parsing) — no Telegram, no Firestore
  data/        DataAccess + FirebaseRepository (the Firestore boundary)
  Enums/  Utils/   shared cross-cutting code
```

A change to one capability should touch one `features/<slice>` folder, not ripple
across horizontal layers.

## How a request flows

1. A Telegram update reaches **`NodeHandler`**, which routes: plain text → the
   feature **Node** for the user's `UserState`, an inline-button tap → the
   **CallbackNode** owning the callback-data prefix (`EV#` events, `AP#` admin menu,
   `ROLES#` role assignment; old-format attendance buttons are adapted, any other
   pre-redesign button gets an "expired menu" notice). Callback nodes are additionally
   role-gated (`CallbackNode.required_roles`).
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
  builds on (see ADR 0001).
- **Inline-first menus, static reply keyboard.** The reply keyboard is a fixed,
  role-filtered top-level menu (Events / Admin / Website / Help) built from the
  DEFAULT node's transitions; everything about a *specific object* (event lists, the
  event card, confirmations, the add-event wizard buttons) lives on inline messages
  edited in place. One event card combines details, live counts, attendance buttons,
  calendar export and — for admins — edit/delete, so there is no separate stats/edit
  navigation.
- **Domain logic in the domain layer.** Business rules (e.g. the ">2h event move
  invalidates attendance" policy, datetime parsing/validation) live in `domain/`, not
  inside view nodes.
- **Event type is data, not code paths.** Game / Training / Timekeeping are handled by
  one polymorphic flow parameterized by `Event`, not by three copy-pasted handlers.
- **Wizard/edit step lives in context, not the state machine.** The add-event wizard's
  current field *and event type* are held in the draft (`TempData`); the field edit
  carries its context in `UsersToState.additional_info`. `UserState` therefore only
  models *which typed input is expected* — six states total (INIT, DEFAULT, the three
  typed-input states, REJECTED); all menu navigation is inline.
- **Typed-input states can't strand the user.** The keyboard stays visible during
  typed input, and its main-menu commands act as escape hatches: they clean up the
  in-flight flow (drop the draft / staged input) and navigate.
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

- **Observability.** Unhandled exceptions in the interactive path (`NodeHandler`,
  `Node`) and the background jobs (`SchedulingService`) all route through
  `TelegramService.report_exception`, which logs at ERROR with a traceback *first*
  (a greppable, alertable signal that survives even when the maintainer DM fails) and
  then best-effort alerts the maintainer. A dedicated metrics system or error-tracking
  integration (e.g. Sentry) is a possible next step but not currently wired.
- **Trigger system** (`TriggerService.initialize_triggers`, trigger mechanics in
  `framework/Triggers/`) is wired but underused — revisit when a second trigger is
  needed.

Candidate next work — features and technical follow-ups, each with an entry point and
rough effort — is tracked in [`todos.md`](../todos.md).
