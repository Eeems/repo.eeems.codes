import contextlib
import os
import sys
import subprocess

from traceback import format_exc


@contextlib.contextmanager
def pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    try:
        yield

    finally:
        os.chdir(previousDir)


def run(args, env=None, stdin=None):
    try:
        subprocess.check_call(
            args, stdout=sys.stdout, stderr=subprocess.STDOUT, env=env, stdin=stdin
        )
        return True

    except subprocess.CalledProcessError as ex:
        print(f"  Process exited with code {ex.returncode}")
        return False

    except Exception:
        print(f"  {format_exc(0).strip()}")
        return False
