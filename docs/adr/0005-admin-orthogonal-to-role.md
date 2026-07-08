# ADR 0005: Admin is a flag, orthogonal to the membership role

## Status
Accepted (2026-07-08)

## Context
`Role` was one enum holding both a user's playing state (PLAYER / RETIRED /
INACTIVE / SPECTATOR plus the INIT / REJECTED lifecycle stances) and ADMIN.
Because ADMIN sat inside `RoleSet.ACTIVE_PLAYERS`, an admin was *by definition*
an active player: they received attendance reminders, appeared in every
attendance overview and counted toward the low-attendance trigger — even if
they no longer played. Conversely a player promoted to ADMIN silently lost the
RETIRED/INACTIVE distinction, because one enum slot cannot hold two facts.

## Decision
**Two independent facts on `UsersToState`:**
- `role: Role` — the membership state (`INIT / PLAYER / SPECTATOR / RETIRED /
  INACTIVE / REJECTED`). ADMIN is removed from the enum.
- `is_admin: bool` (Firestore `isAdmin`) — may combine with any role.

Admin dictates only which menus and interactions are available; the role alone
decides reminder fan-outs, overviews and attendance.

**Gating via `Audience` (replaces `RoleSet`).** A frozen dataclass of
`(roles, includes_admins)` with `allows(user_to_state)`; transitions and
callback nodes are checked against the whole `UsersToState`, not a bare role.
`EVERYONE` sets `includes_admins=True` so a retired or inactive admin still
reaches the main menus; `PLAYERS` / `ACTIVE_PLAYERS` deliberately do NOT — an
admin attends because of their role, never because of the flag.

**Data migration: rewrite, plus self-heal.** `scripts/
migrate_admin_role_to_flag.py` rewrites stored role 42 (legacy ADMIN) to
PLAYER + `isAdmin=true` and stamps `isAdmin=false` elsewhere. The entity heals
stragglers on read (ADR 0002 pattern), but the migration is NOT optional:
Firestore roster queries filter on the *stored* values (`role == PLAYER`,
`isAdmin == true`), so unmigrated admins would drop out of every roster view.
Legacy inline buttons that encode role 42 map to the new model preserving their
original meaning: `ROLES#R#42` shows the admin list, `ROLES#A#…#42` is an
idempotent admin grant (never a toggle - the old button could not demote).

**Lifecycle of the flag.** `join_team` preserves an existing bit (a healed
admin re-/starting is not demoted — and keeps their membership role too) and
only grants it explicitly (team registration stamps the first admin PLAYER +
flag). `leave_team` and the `UserStateService.reject` seam clear it — no team,
no admin. The roles menu toggles it independently of the role buttons, guarded:
the target must still be a team member, and the last admin cannot be removed.

## Consequences
- A retired/inactive admin gets no reminders, no announce DMs, and appears in
  no attendance summary or statistics overview — the feature this ADR exists for.
- The trainer roster picker lists active players only, as before; a non-playing
  admin can still be a trainer only as a stray seeded id.
- Old menus (>48h) keep working: ROLES# buttons carrying 42 act on the flag.
