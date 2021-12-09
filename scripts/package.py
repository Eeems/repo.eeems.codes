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


class Package(BaseConfig):
    def __init__(self, data, name=None):
        self._data = data
        if name is not None:
            self._data["name"] = name

        if self.name in PackageConfig.packages:
            raise ConfigException(f"Package {self.name} already exists")

        PackageConfig.packages[self.name] = self

    def __repr__(self):
        return f"<Package {self.name}>"

    def validate(self):
        self.name

    @property
    def git(self):
        return self._data.get("git", f"https://aur.archlinux.org/{self.name}.git")

    @property
    def private(self):
        return self._data.get("private", False)

    @property
    def name(self):
        return self._data["name"]

    @property
    def script(self):
        return self._data.get("script", None)

    @property
    def image(self):
        return self._data.get("image", "registry.eeems.codes/archlinux:latest")

    @property
    def depends(self):
        return [PackageConfig.packages[x] for x in self._data.get("depends", [])]

    def build(self):
        pass


class PackageConfig(BaseConfig):
    packages = {}

    def __init__(self, path):
        self.path = os.path.realpath(path)
        with open(self.path) as f:
            self._data = yaml.load(f, Loader=yaml.SafeLoader) or {}

        if isinstance(self._data, list):
            for data in self._data:
                Package(data).validate()

        else:
            name = os.path.splitext(os.path.basename(path))[0]
            Package(self._data, name).validate()

    def __repr__(self):
        return f"<PackageConfig {self.path}>"

    @staticmethod
    def validate():
        for package in PackageConfig.packages.values():
            package.depends
