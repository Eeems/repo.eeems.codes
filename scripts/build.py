import sys
import argparse
import util
import glob


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


def main(argv):
    main.args = parser.parse_args(argv)
    with util.pushd(main.args.reposdir):
        for repoPath in glob.iglob("*/"):
            for packagePath in glob.iglob(f"{repoPath}/*.yml"):
                try:
                    PackageConfig(packagePath)

                except Exception:
                    print(f"Failed handling {packagePath}: {format_exc(0).strip()}")

    print(f"Packages: {PackageConfig.packages}")
    PackageConfig.validate()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])

    except Exception:
        print("Error encountered:\n" + format_exc().strip())
        sys.exit(1)
