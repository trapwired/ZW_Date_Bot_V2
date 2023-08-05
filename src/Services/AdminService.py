from Data import DataAccess


class AdminService(object):
    def __init__(self, data_access: DataAccess):
        self.data_access = data_access
