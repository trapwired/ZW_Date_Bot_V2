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


class ObjectNotFoundException(Exception):
    pass


class MissingCommandDescriptionException(Exception):
    def __init__(self, missing_commands):
        message = 'We are missing a description for the following commands: ' + ', '.join(missing_commands)
        super().__init__(message)
