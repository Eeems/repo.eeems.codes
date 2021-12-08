import contextlib
import os


@contextlib.contextmanager
def pushd(newDir):
    previousDir = os.getcwd()
    os.chdir(newDir)
    try:
        yield

    finally:
        os.chdir(previousDir)
