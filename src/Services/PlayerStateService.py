from src.Data import DataAccess


class PlayerStateService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access
