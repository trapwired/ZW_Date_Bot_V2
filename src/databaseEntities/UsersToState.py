from Enums.Role import Role
from Enums.UserState import UserState


class UsersToState(object):
    def __init__(self, user_id: str, state: UserState, additional_info: str = '', role: Role = Role.INIT,
                 doc_id: str = None):
        self.doc_id = doc_id
        self.user_id = user_id
        self.state = state
        self.additional_info = additional_info
        self.role = role

    @staticmethod
    def from_dict(doc_id: str, source: dict):
        return UsersToState(
            source['userId'],
            source['state'],
            source['additionalInformation'],
            source['role'],
            doc_id, )

    def add_role(self, role: Role):
        self.role = role
        return self

    def add_document_id(self, doc_id: str):
        self.doc_id = doc_id
        return self

    def to_dict(self):
        return {'userId': self.user_id,
                'state': self.state,
                'additionalInformation': self.additional_info,
                'role': self.role}

    def __repr__(self):
        return f"PlayerToState(userId={self.user_id}, state={UserState(self.state)}, additionalInfo={self.additional_info}, doc_id={self.doc_id}, role={self.role})"
