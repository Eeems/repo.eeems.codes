import sys
import argparse
import util
import glob


from package import PackageConfig

parser = argparse.ArgumentParser(
    prog="build", description="build packages", add_help=True
)
parser.add_argument("--version", action="version", version="0.1")
parser.add_argument(
    "packagesdir",
    help="Directory that contains all the packages to build",
    default=None,
)


def main(argv):
    main.args = parser.parse_args(argv)
    packages = {}
    with util.pushd(main.args.packagesdir):
        for path in glob.iglob("*.yml"):
            try:
                package = PackageConfig(path)
                package.validate()
                if package.name in packages:
                    raise Exception(f"Package {package.name} already defined")

                packages[package.name] = package

            except Exception as ex:
                print(ex)

    print(packages)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])

    except Exception:
        from traceback import format_exc

        print("Error encountered:\n" + format_exc().strip())
        sys.exit(1)
