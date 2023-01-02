import contextlib
import os
import sys
import subprocess
import platform

from traceback import format_exc
from blessed import Terminal


@contextlib.contextmanager
def pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    try:
        yield

    finally:
        os.chdir(previousDir)


def run(args, env=None, stdin=None, chronic=False):
    try:
        if chronic:
            subprocess.check_output(
                args,
                stderr=subprocess.STDOUT,
                env=env,
                stdin=stdin,
            )
        else:
            subprocess.check_call(
                args,
                stdout=sys.stdout,
                stderr=subprocess.STDOUT,
                env=env,
                stdin=stdin,
            )
        return True

    except subprocess.CalledProcessError as ex:
        if chronic:
            print(ex.output.decode())

        print(f"  Process exited with code {ex.returncode}")
        return False

    except Exception:
        print(f"  {format_exc(0).strip()}")
        return False


def sudo_rm(path):
    if not run(["sudo", "-n", "rm", "-rf", path], chronic=True):
        raise Exception(f"Failed to remove {path}")


def term():
    if not hasattr(term, "_handle"):
        term._handle = Terminal()

    return term._handle
