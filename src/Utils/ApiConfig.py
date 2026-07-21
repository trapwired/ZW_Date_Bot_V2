import configparser

from Utils import PathUtils

_REQUIRED = object()


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

    def get_key(self, section: str, identifier: str, default=_REQUIRED):
        # With a default, a missing section/key is a legitimate "not configured" - only
        # this class knows configparser's exception types, so callers never import it.
        try:
            return self.api_config.get(section, identifier)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is _REQUIRED:
                raise
            return default

    def get_bool(self, section: str, identifier: str):
        return str2bool(self.get_key(section, identifier))
