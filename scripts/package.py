import yaml
import os
import io
import tempfile
import util


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
    def __init__(self, repo, data, name=None):
        self._data = data
        self._cache = {}
        self.built = False
        if name is not None:
            self._data["name"] = name

        if self.name in PackageConfig.packages:
            raise ConfigException(f"Package {self.name} already exists")

        if repo not in PackageConfig.repos:
            self.repo = Repo(repo)

        else:
            self.repo = PackageConfig.repos[repo]

        PackageConfig.packages[self.name] = self

    def __repr__(self):
        return f"<Package {self.name}>"

    def validate(self):
        self.name

    @property
    def ignore(self):
        return self._data.get("ignore", False)

    @property
    def git(self):
        return self._data.get("git", f"https://aur.archlinux.org/{self.name}.git")

    @property
    def name(self):
        return self._data["name"]

    @property
    def script(self):
        return self._data.get("script", None)

    @property
    def cleanup(self):
        return self._data.get("cleanup", None)

    @property
    def image(self):
        return self._data.get("image", "registry.eeems.codes/archlinux:latest")

    @property
    def depends(self):
        if "depends" not in self._cache:
            self._cache["depends"] = [
                PackageConfig.packages[x] for x in self._data.get("depends", [])
            ]

        return self._cache["depends"]

    __entry_package = None

    @property
    def full_depends(self):
        if "full_depends" not in self._cache:
            if Package.__entry_package is None:
                Package.__entry_package = self

            elif Package.__entry_package is self:
                raise ConfigException(f"Dependency loop detected for {self.name}")

            packages = []
            for package in self.depends:
                for depend in package.full_depends:
                    packages.append(depend)

                if package not in packages:
                    packages.append(package)

            self._cache["full_depends"] = packages
            Package.__entry_package = None

        return self._cache["full_depends"]

    def build(self):
        print(f"=> Building {self.name}")
        with tempfile.TemporaryDirectory(
            dir=os.environ.get("WORKDIR", None)
        ) as tmpdirname:
            env = os.environ.copy()
            env[
                "GIT_SSH_COMMAND"
            ] = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
            if not util.run(
                ["git", "clone", "--depth=1", self.git, os.path.join(tmpdirname)], env
            ):
                print("  Failed to checkout repo")
                return

            args = [
                "docker",
                "run",
                f"--volume={os.path.realpath('.')}:/pkg/ci:ro",
                f"--volume={tmpdirname}:/pkg/pkg:rw",
                f"--volume={os.path.realpath('cache')}:/pkg/cache:rw",
                f"--volume={os.path.realpath('packages')}:/pkg/packages:rw",
                "-e",
                "GPG_PRIVKEY",
                "-e",
                "GPGKEY",
            ]
            if self.script is not None:
                args + ["-e", "SETUP_SCRIPT"]
                env["SETUP_SCRIPT"] = self.script

            if self.cleanup is not None:
                args + ["-e", "CLEANUP_SCRIPT"]
                env["CLEANUP_SCRIPT"] = self.cleanup

            self.built = util.run(
                args
                + [
                    self.image,
                    "bash",
                    "ci/scripts/package.sh",
                ],
                env,
            )


class Repo(object):
    def __init__(self, name):
        if name is None:
            raise ConfigException("Unable to create a repo without a name")

        if name in PackageConfig.repos:
            raise ConfigException(f"Repo {name} already exists")

        PackageConfig.repos[name] = self
        self.name = name

    @property
    def packages(self):
        return [
            x
            for x in PackageConfig.packages.values()
            if not x.ignore and x.repo is self
        ]

    def publish(self):
        print(f"=> Publishing {self.name}")


class PackageConfig(BaseConfig):
    repos = {}
    packages = {}

    def __init__(self, repo, path):
        self.path = os.path.realpath(path)
        with open(self.path) as f:
            self._data = yaml.load(f, Loader=yaml.SafeLoader) or {}

        if isinstance(self._data, list):
            for data in self._data:
                Package(repo, data).validate()

        else:
            name = os.path.splitext(os.path.basename(path))[0]
            Package(repo, self._data, name).validate()

    def __repr__(self):
        return f"<PackageConfig {self.path}>"

    @staticmethod
    def validate():
        [x for x in PackageConfig.sorted_packages()]

    @staticmethod
    def sorted_packages():
        packages = []
        for package in PackageConfig.packages.values():
            if package.ignore:
                continue

            for depend in package.full_depends:
                if depend not in packages:
                    packages.append(depend)

            if package not in packages:
                packages.append(package)

        return packages

    @staticmethod
    def build():
        for package in PackageConfig.sorted_packages():
            package.build()

    @staticmethod
    def publish():
        for repo in PackageConfig.repos.values():
            repo.publish()
