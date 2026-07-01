# ADR 0001 — Multi-team tenancy: scope at the data boundary, one team per Telegram user

- **Status:** Accepted
- **Date:** 2026-06-30
- **Deciders:** Dominic Weibel
- **Context:** decided during the node-thinning work; implemented after the physical reslice (now complete).

## Context

The bot is currently **single-tenant**: one global website URL, one global set of
events (Game/Training/Timekeeping tables), one global roster and role set. The
long-running goal is to let **more than one team** use the same bot instance.

Multi-team is multi-tenancy, and the dominant risk in multi-tenancy is
**cross-tenant data leakage**: a single query that forgets its team filter and
returns another team's events, attendance, or roster. The structural defense is
to minimize the number of places that touch data, so the team filter is applied
in a few auditable seams instead of being sprinkled across every call site.

Two questions had to be settled before tenancy can be designed:

1. **Where does the team filter live?** (the scoping mechanism)
2. **Can one Telegram user belong to more than one team?** (the identity model)

The node-thinning sweep (PRs #8–#11) is the relevant enabler: every
*feature* node now reaches data through a small set of services
(`EventService`, `AttendanceService`, `StatisticsService`, `RoleService`,
`WebsiteService`, `UserStateService`) rather than calling `DataAccess` directly.
That collapses ~50+ scattered data-access call sites into a handful of service
methods on top of the single `DataAccess`/`FirebaseRepository` boundary.

## Decision

### 1. One Telegram user interacts with exactly one team

A `(telegram_id) → team` lookup is a **total function**. We do **not** support a
person belonging to multiple teams at once. This keeps team resolution stateless
(no per-interaction "current team" selector) and avoids entangling tenancy with
the `UserState` collapse.

If the multi-team-per-user requirement ever appears, it is a **new ADR that
supersedes this one** — it would reintroduce a per-interaction current-team
context and is explicitly out of scope here.

### 2. Scope at the data boundary, off an ambient tenant context

Tenancy is enforced at the **`DataAccess`/`FirebaseRepository` boundary**, not by
threading a `team_id` parameter through every service method:

- Resolve the team **once per update** (from the Telegram chat/user) into an
  ambient `TenantContext`.
- `DataAccess`/`FirebaseRepository` applies the team filter to **every** query
  off that context (team-partitioned collections, or a `teamId` field filtered
  on every read/write).
- Feature services stay mostly pass-through; they consume the context, they don't
  each re-implement the filter.

The goal is **exactly one place** a query can be unscoped — auditable, testable,
and hard to bypass — rather than O(call sites) places that must each remember.

**Anti-goal:** sprinkling `team_id` arguments across the service API. That just
moves the "easy to forget" leak from nodes to services.

## Consequences

**Positive**
- The service layer is the right shape for this: tenant scoping lands in
  a handful of seams plus the data boundary, not in 18 view nodes.
- `UserStateService.register_user(user)` is the single place a user is created —
  the natural spot to stamp the user's team on join.
- Single-team-per-user keeps team resolution a pure function and keeps the state collapse
  independent of tenancy.

**Negative / cost**
- The data layer is the heavy lift: `FirebaseRepository` must move from global
  tables to team-partitioned data, and `SchedulingService`'s global
  reminder/summary loops must become per-team loops (this one is outside the
  node→service work — flag it when tenancy starts).
- A bootstrapping/onboarding flow is needed to create a team and bind the first
  admin.

**Follow-ups to close before/with implementation**
- The base `Node.get_commands_for_buttons` still reads `data_access` directly
  (`get_user`, `get_all_event_attendances`) — the one accepted exception.
  It must become tenant-aware too; it lives in `framework/Nodes/Node.py`, a single
  known location, not scatter.
- Decide team-partitioning strategy at the Firestore level (subcollections per
  team vs. a `teamId` field + composite indexes).

## Related

- `docs/ARCHITECTURE.md` — the service seams, the reslice, and the base-Node read that
  this ADR refines.
