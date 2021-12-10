import os
import sys
import argparse
import util
import glob
import tempfile


from package import PackageConfig
from traceback import format_exc

parser = argparse.ArgumentParser(
    prog="build", description="build packages", add_help=True
)
parser.add_argument("--version", action="version", version="0.1")
parser.add_argument(
    "reposdir",
    help="Directory that contains directories for each repository. "
    "Each directory will contain yml files of package descriptions",
    default=None,
)
parser.add_argument("package", help="Build a specific package", nargs="?", default=None)
parser.add_argument(
    "--stats", action="store_true", help="Show information about the repos"
)
parser.add_argument("--verbose", action="store_true", help="Show verbose logs")


def main(argv):
    if not os.path.exists("cache"):
        os.mkdir("cache")

    if not os.path.exists("packages"):
        os.mkdir("packages")

    if "WORKDIR" not in os.environ:
        os.environ["WORKDIR"] = os.path.join(tempfile.gettempdir(), "repo.eeems.codes")

    if not os.path.exists(os.environ["WORKDIR"]):
        os.mkdir(os.environ["WORKDIR"])

    main.args = parser.parse_args(argv)
    if main.args.verbose:
        os.environ["VERBOSE"] = "1"

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
    if main.args.stats:
        print(f"Repositories: {len(PackageConfig.repos)}")
        print("Packages")
        for repo in PackageConfig.repos.values():
            print(f"  {repo.name}: {len(repo.packages)}")

        print(f"  Total: {len(PackageConfig.packages)}")
        return

    if main.args.verbose:
        print(f"Working Directory: {os.environ['WORKDIR']}")

    if main.args.package is not None:
        if main.args.package not in PackageConfig.packages:
            raise Exception(f"Package {main.args.package} not found")

        package = PackageConfig.packages[main.args.package]
        package.build()
        if not package.built:
            raise Exception("Failed to build")

        package.repo.publish()
        return

    PackageConfig.build()
    PackageConfig.publish()
    if PackageConfig.failed():
        raise Exception("One or more build failed")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])

    except Exception:
        print(util.term().red("Error encountered:\n" + format_exc().strip()))
        sys.exit(1)
