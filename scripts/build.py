#!/usr/bin/env python
import os
import sys
import argparse
import util
import glob
import json
import tempfile


from package import PackageConfig
from traceback import format_exc

actions = {}

parser = argparse.ArgumentParser(
    prog="build", description="build packages", add_help=True
)
parser.add_argument("--version", action="version", version="0.1")
parser.add_argument("--verbose", action="store_true", help="Show verbose logs")
parser.add_argument(
    "--repos-dir",
    dest="reposdir",
    help="Directory that contains directories for each repository. "
    "Each directory will contain yml files of package descriptions",
    default="repos",
)
subparsers = parser.add_subparsers(dest="action")


def noop(*args, **kwds):
    pass


def action(fn):
    fn.parser = subparsers.add_parser(fn.__name__)
    it = fn(fn.parser)
    next(it)
    actions[fn.__name__] = it
    return noop


@action
def info(parser):
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output json information for use in a github action matrix",
    )
    yield
    if main.args.json:
        print(
            json.dumps(
                {
                    "include": [
                        {
                            "repo": x.repo.name,
                            "package": x.name,
                            "runner": x.runner,
                            "image": x.image,
                        }
                        for x in PackageConfig.sorted_packages()
                    ]
                }
            )
        )
        return

    for repo in PackageConfig.repos.values():
        for package in repo.packages:
            print(f"{repo.name}/{package.name}:")
            print(f"  git: {package.git}")
            if package.branch:
                print(f"  branch: {package.branch}")
            print(f"  image: {package.image}")
            print(f"  runner: {package.runner}")
            if package.depends:
                print(f"  depends: {', '.join([x.name for x in package.depends])}")
            if package.makedepends:
                print(f"  make depends: {', '.join(package.makedepends)}")


@action
def stats(parser):
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output json information for use in a github action matrix",
    )
    yield
    if main.args.json:
        print(
            json.dumps(
                {
                    "include": [
                        {"repo": x.name, "image": x.image, "packages": len(x.packages)}
                        for x in PackageConfig.repos.values()
                    ]
                }
            )
        )
        return

    print(f"Repositories: {len(PackageConfig.repos)}")
    print("Packages")
    for repo in PackageConfig.repos.values():
        print(f"  {repo.name}: {len(repo.packages)}")

    print(f"  Total: {len(PackageConfig.packages)}")


def _setup_paths():
    if not os.path.exists("cache"):
        os.mkdir("cache")

    if not os.path.exists("packages"):
        os.mkdir("packages")

    if not os.path.exists("repo"):
        os.mkdir("repo")

    if "WORKDIR" not in os.environ:
        os.environ["WORKDIR"] = os.path.join(tempfile.gettempdir(), "repo.eeems.codes")

    if not os.path.exists(os.environ["WORKDIR"]):
        os.mkdir(os.environ["WORKDIR"])

    if main.args.verbose:
        print(f"Working Directory: {os.environ['WORKDIR']}")


@action
def publish(parser):
    parser.add_argument("repo", help="Publish a repo", default=None)
    yield
    _setup_paths()
    if main.args.repo not in PackageConfig.repos:
        raise Exception(f"Repo {main.args.repo} not found")

    repo = PackageConfig.repos[main.args.repo]
    repo.publish()
    if not repo.published:
        raise Exception("Publish failed")


def _build_all():
    PackageConfig.build()
    PackageConfig.publish()
    if PackageConfig.failed():
        raise Exception("One or more build failed")


def _build_repo(name):
    if name not in PackageConfig.repos:
        raise Exception(f"Repo {name} not found")

    repo = PackageConfig.repos[name]
    repo.build()
    if repo.failed:
        raise Exception("One or more build failed")


def _build_package(name):
    if name not in PackageConfig.packages:
        raise Exception(f"Package {name} not found")

    package = PackageConfig.packages[name]
    package.build()
    if not package.built:
        raise Exception("Failed to build")


@action
def build(parser):
    parser.add_argument(
        "type",
        help="Type of build to run",
        default="all",
        choices=["all", "repo", "package"],
    )
    parser.add_argument(
        "thing",
        help="Repo or package to build if type is not 'all'",
        default=None,
        nargs="?",
    )
    parser.add_argument(
        "--package", help="Build a specific package", nargs="?", default=None
    )
    parser.add_argument("--repo", help="Build a repo", default=None)
    yield
    _setup_paths()
    if main.args.type == "repo":
        _build_repo(main.args.thing)

    elif main.args.type == "package":
        _build_package(main.args.thing)

    elif main.args.type == "all":
        _build_all()


def main(argv):
    main.args = parser.parse_args(argv)
    if main.args.verbose:
        os.environ["VERBOSE"] = "1"

    if main.args.action is None:
        parser.print_help()
        return

    t = util.term()
    with util.pushd(main.args.reposdir):
        for repo in glob.iglob("*/"):
            for packagePath in glob.iglob(f"{repo}/*.yml"):
                try:
                    PackageConfig(os.path.dirname(repo), packagePath)

                except Exception:
                    print(
                        t.red(f"Failed handling {packagePath}: {format_exc(0).strip()}")
                    )

    PackageConfig.validate()
    [x for x in actions[main.args.action]]


if __name__ == "__main__":
    try:
        main(sys.argv[1:])

    except Exception:
        print(util.term().red("Error encountered:\n" + format_exc().strip()))
        sys.exit(1)
