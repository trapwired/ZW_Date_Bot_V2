class ExpectedException(Exception):
    """Marker for known, control-flow exceptions (e.g. a lookup miss). These are logged for
    traceability but do not raise a maintainer alert, so alerts stay reserved for real bugs."""
    pass


class DocumentIdNotPresentException(Exception):
    pass


class MoreThanOneDBHitException(Exception):
    pass


class MoreThanOneObjectFoundException(Exception):
    pass


class NodesMissingException(Exception):
    def __init__(self, missing_states):
        message = 'We are missing the following states as nodes: ' + ', '.join(str(s.name) for s in missing_states)
        super().__init__(message)


class ObjectNotFoundException(ExpectedException):
    def __init__(self, collection, doc_ref):
        message = f'\"{doc_ref}\" does not exist in \"{collection}\"'
        super().__init__(message)


class NoEventFoundException(Exception):
    pass


class NoTempDataFoundException(ExpectedException):
    pass


class TooManyObjectsFoundException(Exception):
    pass


class MissingCommandDescriptionException(Exception):
    def __init__(self, missing_commands):
        message = 'We are missing a description for the following commands: ' + ', '.join(missing_commands)
        super().__init__(message)


class GroupChatAlreadyRegisteredException(ExpectedException):
    def __init__(self, group_chat_id):
        message = f'A team is already registered for group chat "{group_chat_id}"'
        super().__init__(message)


class SpectatorPasswordNotAllowedException(ExpectedException):
    """Empty or reserved - a password that could never admit a spectator."""


class SpectatorPasswordAlreadyTakenException(ExpectedException):
    def __init__(self):
        super().__init__('This spectator password is already taken by another team')
