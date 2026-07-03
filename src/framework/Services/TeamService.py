from data.DataAccess import DataAccess
from data.TenantContext import current_team_id
from domain.entities.Team import Team
from Utils.CustomExceptions import (GroupChatAlreadyRegisteredException, ObjectNotFoundException,
                                    SpectatorPasswordAlreadyTakenException,
                                    SpectatorPasswordNotAllowedException)


class TeamService:
    """Registry of teams and the per-team lookups the framework needs. Caches the
    (tiny) team list; the bot is a single writer process, so invalidating on our own
    writes keeps the cache correct."""

    def __init__(self, data_access: DataAccess):
        self.data_access = data_access
        self._all_teams: list[Team] | None = None

    def get_all_teams(self) -> list[Team]:
        if self._all_teams is None:
            self._all_teams = self.data_access.get_all_teams()
        return self._all_teams

    def current_team(self) -> Team:
        return self.get_team(current_team_id())

    def get_team(self, team_id: str) -> Team:
        for team in self.get_all_teams():
            if team.doc_id == team_id:
                return team
        # Not in cache (e.g. created by migration while running) - refresh once.
        self._all_teams = None
        for team in self.get_all_teams():
            if team.doc_id == team_id:
                return team
        raise ObjectNotFoundException('teams', team_id)

    def find_team_by_group_chat(self, group_chat_id) -> Team | None:
        for team in self.get_all_teams():
            if team.group_chat_id == int(group_chat_id):
                return team
        return None

    def find_team_by_spectator_password(self, password: str) -> Team | None:
        for team in self.get_all_teams():
            if team.spectator_password and team.spectator_password == password:
                return team
        return None

    def register_team(self, name: str, group_chat_id: int) -> Team:
        """One team per group chat - the group IS the team's identity anchor."""
        if self.find_team_by_group_chat(group_chat_id) is not None:
            raise GroupChatAlreadyRegisteredException(group_chat_id)
        team = self.data_access.add(Team(name, group_chat_id))
        self._all_teams = None
        return team

    # Case-insensitive because the REJECTED screen's help transitions match lowercased
    # input BEFORE the password fallback - these words could never admit anyone.
    RESERVED_SPECTATOR_PASSWORDS = {'help', '/help'}
    # The password is the only thing between a stranger and a team's attendance data;
    # trivially guessable ones must not be storable in the first place.
    MIN_SPECTATOR_PASSWORD_LENGTH = 6

    def set_spectator_password(self, team: Team, password: str) -> None:
        """The password identifies the team at entry, so it must be unique across teams
        and actually enterable - both halves of the invariant live here."""
        if len(password or '') < self.MIN_SPECTATOR_PASSWORD_LENGTH \
                or password.lower() in self.RESERVED_SPECTATOR_PASSWORDS:
            raise SpectatorPasswordNotAllowedException()
        other = self.find_team_by_spectator_password(password)
        if other is not None and other.doc_id != team.doc_id:
            raise SpectatorPasswordAlreadyTakenException()
        team.spectator_password = password
        try:
            self.data_access.update(team)
        finally:
            # Also on failure: the cached Team was already mutated above, so force the
            # next read to refetch the persisted truth instead of a phantom password.
            self._all_teams = None

    def update_team(self, team: Team) -> None:
        self.data_access.update(team)
        self._all_teams = None
