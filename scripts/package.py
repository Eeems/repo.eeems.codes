import yaml
import os


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
        self.path = os.path.realpath(path)
        with open(self.path) as f:
            self._data = yaml.load(f, Loader=yaml.SafeLoader) or {}

        if "name" not in self._data:
            self._data["name"] = os.path.splitext(os.path.basename(path))[0]

    def __repr__(self):
        return f"<PackageConfig {self.name}>"

    @property
    def name(self):
        return self._data["name"]

    def validate(self):
        pass
