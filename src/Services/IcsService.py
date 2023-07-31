from src.Data import DataAccess


class IcsService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access
