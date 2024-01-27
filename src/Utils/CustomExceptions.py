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
    def __init__(self, collection, doc_ref):
        message = f'\"{doc_ref}\" does not exist in \"{collection}\"'
        super().__init__(message)


class NoEventFoundException(Exception):
    pass


class NoTempDataFoundException(Exception):
    pass


class TooManyObjectsFoundException(Exception):
    pass


class MissingCommandDescriptionException(Exception):
    def __init__(self, missing_commands):
        message = 'We are missing a description for the following commands: ' + ', '.join(missing_commands)
        super().__init__(message)
