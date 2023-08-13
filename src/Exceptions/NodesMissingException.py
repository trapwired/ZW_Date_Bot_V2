class NodesMissingException(Exception):
    def __init__(self, missing_states):
        message = 'We are missing the following states as nodes: ' + ', '.join(str(s.name) for s in missing_states)
        super().__init__(message)
