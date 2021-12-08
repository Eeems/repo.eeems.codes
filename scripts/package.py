import yaml


class ConfigException(Exception):
    pass


class BaseConfig(object):
    def __getitem__(self, name):
        return self._data[name]

    def __contains__(self, name):
        return name in self._data

    def __str__(self):
        return yaml.dump(self._data, default_flow_style=False)


class PackageConfig(BaseConfig):
    def __init__(self, path):
        self.path = path
