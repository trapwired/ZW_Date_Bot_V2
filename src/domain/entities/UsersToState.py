from Enums.Role import Role, LEGACY_ADMIN_ROLE_VALUE
from Enums.UserState import UserState

from domain.entities.DatabaseEntity import DatabaseEntity


def get_role(role: Role | str | int) -> Role:
    if type(role) is str:
        return Role(int(role))
    if type(role) is int:
        return Role(role)
    return role


class UsersToState(DatabaseEntity):
    def __init__(self, user_id: str, state: UserState, additional_info: str = '', role: Role = Role.INIT,
                 team_id: str | None = None, language: str | None = None, doc_id: str = None,
                 is_admin: bool = False):
        super().__init__(doc_id)
        self.user_id = user_id
        if type(state) is str or type(state) is int:
            state = UserState(int(state))
        self.state = state
        self.additional_info = additional_info

        # Pre-refactor documents stored ADMIN as a role; heal to the orthogonal model
        # (the migration script rewrites the DB, this catches stragglers).
        if role in (LEGACY_ADMIN_ROLE_VALUE, str(LEGACY_ADMIN_ROLE_VALUE)):
            role = Role.PLAYER
            is_admin = True
        self.role = get_role(role)
        self.is_admin = is_admin
        self.team_id = team_id
        # None = never explicitly chosen; the client's language_code decides per update.
        self.language = language

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return UsersToState(
            source['userId'],
            source['state'],
            source['additionalInformation'],
            source['role'],
            source.get('teamId'),
            source.get('language'),
            doc_id,
            source.get('isAdmin', False), )

    def add_role(self, role: Role):
        self.role = role
        return self

    def to_dict(self):
        return {'userId': self.user_id,
                'state': self.state,
                'additionalInformation': self.additional_info,
                'role': self.role,
                'isAdmin': self.is_admin,
                'teamId': self.team_id,
                'language': self.language}

    def __repr__(self):
        return f"UserToState(userId={self.user_id}, state={UserState(self.state)}, additionalInfo={self.additional_info}, doc_id={self.doc_id}, role={self.role}, is_admin={self.is_admin}, team_id={self.team_id})"
