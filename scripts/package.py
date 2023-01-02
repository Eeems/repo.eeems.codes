import yaml
import os
import io
import glob
import util
import shutil


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
    def branch(self):
        return self._data.get("branch", None)

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
    def runner(self):
        return self._data.get("runner", "ubuntu-latest")

    @property
    def makedepends(self):
        return self._data.get("makedepends", [])

    @property
    def depends(self):
        if "depends" not in self._cache:
            self._cache["depends"] = []
            for name in self._data.get("depends", []):
                if name not in PackageConfig.packages:
                    raise ConfigException(
                        self.name + " has missing dependency: " + name
                    )

                self._cache["depends"].append(PackageConfig.packages[name])

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

    _pulled_images = []

    def build(self):
        t = util.term()
        print(t.green(f"=> Building {self.name}"))
        tmpdirname = os.path.realpath(os.environ.get("WORKDIR"))
        if os.path.exists(tmpdirname):
            shutil.rmtree(tmpdirname, onerror=lambda f, p, e: util.sudo_rm(p))
            os.mkdir(tmpdirname)

        env = os.environ.copy()
        env[
            "GIT_SSH_COMMAND"
        ] = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
        args = []
        if self.branch is not None:
            args = ["-b", self.branch]

        if not util.run(
            ["git", "clone", "--depth=1"] + args + [self.git, tmpdirname],
            env,
            chronic="VERBOSE" not in os.environ,
        ):
            print(t.red("  Failed to checkout repo"))
            return

        if self.image not in Package._pulled_images:
            Package._pulled_images.append(self.image)
            if "VERBOSE" not in os.environ:
                print(t.green(f"  Pulling {self.image}"))

            if not util.run(
                ["docker", "pull", self.image], chronic="VERBOSE" not in os.environ
            ):
                print(t.red("  Failed to pull image"))
                return

        for package in self.full_depends:
            dependsdir = os.path.join(tmpdirname, "depends")

            for file in glob.iglob(f"packages/{package.name}-*.pkg.tar.*"):
                if not os.path.exists(dependsdir):
                    os.mkdir(dependsdir)

                destination = os.path.join(dependsdir, os.path.basename(file))
                try:
                    os.link(file, destination)
                except OSError:
                    shutil.copyfile(file, destination)

        cidirname = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        args = [
            "docker",
            "run",
            "--workdir=/pkg",
            f"--mount=type=bind,src={cidirname},dst=/pkg/ci,readonly",
            f"--mount=type=bind,src={tmpdirname},dst=/pkg/pkg",
            f"--mount=type=bind,src={os.path.realpath('cache')},dst=/pkg/cache",
            f"--mount=type=bind,src={os.path.realpath('packages')},dst=/pkg/packages",
            "-e",
            "GPG_PRIVKEY",
            "-e",
            "GPGKEY",
            "-e",
            "GITHUB_ACTIONS",
            "-e",
            "VERBOSE",
        ]
        if self.script is not None:
            args += ["-e", "SETUP_SCRIPT"]
            env["SETUP_SCRIPT"] = self.script

        if self.cleanup is not None:
            args += ["-e", "CLEANUP_SCRIPT"]
            env["CLEANUP_SCRIPT"] = self.cleanup

        if self.makedepends:
            args += ["-e", "MAKE_DEPENDS"]
            env["MAKE_DEPENDS"] = ";\n".join(
                [
                    "yay -S --cachedir ./cache  --noconfirm " + x
                    for x in self.makedepends
                ]
            )

        self.built = util.run(
            args
            + [
                self.image,
                "bash",
                "ci/scripts/package.sh",
            ],
            env,
        )
        if not os.environ.get("DOCKER_PRUNE", False):
            return

        if not util.run(
            ["docker", "system", "prune", "--force"],
            chronic="VERBOSE" not in os.environ,
        ):
            print(t.red("  Failed prune"))


class Repo(object):
    def __init__(self, name):
        if name is None:
            raise ConfigException("Unable to create a repo without a name")

        if name in PackageConfig.repos:
            raise ConfigException(f"Repo {name} already exists")

        PackageConfig.repos[name] = self
        self.name = name
        self.image = "registry.eeems.codes/archlinux:latest"
        self.published = False

    @property
    def packages(self):
        return [
            x
            for x in PackageConfig.packages.values()
            if not x.ignore and x.repo is self
        ]

    @property
    def sorted_packages(self):
        packages = []
        for package in self.packages.values():
            if package.ignore:
                continue

            for depend in package.full_depends:
                if depend not in packages:
                    packages.append(depend)

            if package not in packages:
                packages.append(package)

        return packages

    @property
    def failed(self):
        return [x for x in self.packages if not x.built]

    def publish(self):
        t = util.term()
        print(t.green(f"=> Publishing {self.name}"))
        tmpdirname = os.path.realpath(os.environ.get("WORKDIR"))
        if os.path.exists(tmpdirname):
            shutil.rmtree(tmpdirname, onerror=lambda f, p, e: util.sudo_rm(p))
            os.mkdir(tmpdirname)

        if self.image not in Package._pulled_images:
            Package._pulled_images.append(self.image)
            if "VERBOSE" not in os.environ:
                print(t.green(f"  Pulling {self.image}"))

            if not util.run(
                ["docker", "pull", self.image], chronic="VERBOSE" not in os.environ
            ):
                print(t.red("  Failed to pull image"))
                return

        cidirname = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        env = os.environ.copy()
        env["REPO_NAME"] = self.name

        self.published = util.run(
            [
                "docker",
                "run",
                "--workdir=/pkg",
                f"--mount=type=bind,src={cidirname},dst=/pkg/ci,readonly",
                f"--mount=type=bind,src={os.path.realpath('repo')},dst=/pkg/repo",
                "-e",
                "GPG_PRIVKEY",
                "-e",
                "GPGKEY",
                "-e",
                "GITHUB_ACTIONS",
                "-e",
                "REPO_NAME",
                "-e",
                "VERBOSE",
                self.image,
                "bash",
                "ci/scripts/repo.sh",
            ],
            env,
        )
        if not os.environ.get("DOCKER_PRUNE", False):
            return

        if not util.run(
            ["docker", "system", "prune", "--force"],
            chronic="VERBOSE" not in os.environ,
        ):
            print(t.red("  Failed prune"))

    def build(self):
        for package in self.sorted_packages:
            if "GITHUB_ACTIONS" in os.environ:
                print(f"::group::{package.name}")

            package.build()
            if "GITHUB_ACTIONS" in os.environ:
                print("::endgroup::")


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
            if "GITHUB_ACTIONS" in os.environ:
                print(f"::group::{package.name}")

            package.build()
            if "GITHUB_ACTIONS" in os.environ:
                print("::endgroup::")

    @staticmethod
    def publish():
        for repo in PackageConfig.repos.values():
            if "GITHUB_ACTIONS" in os.environ:
                print(f"::group::{repo.name}")

            repo.publish()
            if "GITHUB_ACTIONS" in os.environ:
                print("::endgroup::")

    @staticmethod
    def failed():
        return [x for x in PackageConfig.packages.values() if not x.built]
