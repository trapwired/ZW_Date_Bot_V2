import configparser

from Utils import PathUtils


def str2bool(v):
    return v.lower() in ("True", "true", "t", "1", "T")


class ApiConfig:
    def __init__(self):
        api_config = configparser.RawConfigParser()
        api_config.read(PathUtils.get_secrets_file_path('api_config.ini'), encoding='utf8')
        self.api_config = api_config

    def get_int_list(self, section: str, identifier: str):
        config_string = self.get_key(section, identifier)
        return [int(x.strip()) for x in config_string.split(',')]

    def get_key(self, section: str, identifier: str):
        return self.api_config.get(section, identifier)

    def get_bool(self, section: str, identifier: str):
        return str2bool(self.get_key(section, identifier))
