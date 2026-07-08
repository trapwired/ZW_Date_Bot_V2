"""Who may take a transition / press a callback: a set of membership roles, plus
optionally every admin regardless of their role (an inactive or retired admin must
still reach the menus they administrate). Replaces the old RoleSet, where ADMIN was
itself a role inside each set."""
from dataclasses import dataclass

from Enums.Role import Role


@dataclass(frozen=True)
class Audience:
    roles: frozenset
    includes_admins: bool = False

    def allows(self, user_to_state) -> bool:
        return user_to_state.role in self.roles or (self.includes_admins and user_to_state.is_admin)


# REJECTED users only ever act through their own node/onboarding channel (TEAMLESS),
# exactly as under the old RoleSet.
REALLY_EVERYONE = Audience(frozenset(Role) - {Role.REJECTED})
EVERYONE = Audience(frozenset({Role.PLAYER, Role.SPECTATOR, Role.RETIRED}), includes_admins=True)
# Attendance is tied to the membership role alone: an admin attends because they are
# (or were) a player, never because they are an admin.
PLAYERS = Audience(frozenset({Role.PLAYER, Role.RETIRED}))
ADMINS = Audience(frozenset(), includes_admins=True)
TEAMLESS = Audience(frozenset({Role.INIT, Role.REJECTED}))
