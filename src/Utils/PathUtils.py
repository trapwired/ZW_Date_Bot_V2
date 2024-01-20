import os


def get_root_path():
    path = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-3])
    return path


def get_secrets_path():
    return os.path.join(get_root_path(), 'secrets')


def get_ics_files_path():
    return os.path.join(get_root_path(), 'ics_files')


def get_secrets_file_path(filename: str):
    return os.path.join(get_secrets_path(), filename)
