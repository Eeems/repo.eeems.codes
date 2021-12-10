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
parser.add_argument(
    "--stats", action="store_true", help="Show information about the repos"
)


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
    with util.pushd(main.args.reposdir):
        for repo in glob.iglob("*/"):
            for packagePath in glob.iglob(f"{repo}/*.yml"):
                try:
                    PackageConfig(os.path.dirname(repo), packagePath)

                except Exception:
                    print(f"Failed handling {packagePath}: {format_exc(0).strip()}")

    PackageConfig.validate()
    if main.args.stats:
        print(f"Repositories: {len(PackageConfig.repos)}")
        print("Packages")
        for repo in PackageConfig.repos.values():
            print(f"  {repo.name}: {len(repo.packages)}")

        print(f"  Total: {len(PackageConfig.packages)}")

    else:
        PackageConfig.build()
        PackageConfig.publish()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])

    except Exception:
        print("Error encountered:\n" + format_exc().strip())
        sys.exit(1)
