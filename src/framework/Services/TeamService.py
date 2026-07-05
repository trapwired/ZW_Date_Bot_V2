import secrets

from data.DataAccess import DataAccess
from data.TenantContext import current_team_id
from domain.entities.Team import Team
from localization.Languages import SUPPORTED_LANGUAGES
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

    MAX_OUTSTANDING_INVITES = 10

    def create_spectator_invite(self, team: Team) -> str:
        """An unguessable one-time token, carried to the bot as the /start deep-link
        payload. It identifies the team at entry (like the spectator password), so
        it lives on the team doc and dies on redemption."""
        token = secrets.token_urlsafe(12)
        # Cap outstanding invites: minting past the cap silently retires the oldest
        # unused link, so lost links age out instead of staying live forever.
        team.invite_tokens = team.invite_tokens[-(self.MAX_OUTSTANDING_INVITES - 1):] + [token]
        self.update_team(team)
        return token

    def redeem_spectator_invite(self, token: str) -> Team | None:
        """Consume a one-time invite: returns the team and deletes the token, or
        None for unknown/already-used tokens."""
        if not token:
            return None
        for team in self.get_all_teams():
            if token in team.invite_tokens:
                team.invite_tokens.remove(token)
                self.update_team(team)
                return team
        return None

    def set_language(self, team: Team, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f'Unsupported team language: {language}')
        team.language = language
        self.update_team(team)

    def rename_team(self, team: Team, name: str) -> None:
        if not name.strip():
            raise ValueError('Team name must not be empty')
        team.name = name.strip()
        self.update_team(team)

    def delete_team(self, team: Team) -> None:
        """Only for aborted setups (bot removed before the team saw any use) - an
        established team's data is never auto-deleted (ADR 0001: manual cleanup)."""
        self.data_access.delete_team(team)
        self._all_teams = None

    def toggle_trainer(self, event_type, chat_id: int) -> None:
        """Mutate + persist + cache-invalidate in one step so no caller can flip a
        trainer flag on the cached Team and forget the write."""
        team = self.current_team()
        team.toggle_trainer(event_type, chat_id)
        self.update_team(team)

    def update_team(self, team: Team) -> None:
        try:
            self.data_access.update(team)
        finally:
            # Also on failure: callers mutate the cached Team before persisting, so force
            # the next read to refetch the stored truth instead of a phantom edit.
            self._all_teams = None
