"""Start of the command line for bin/keel. Run as a file, so sys.path[0] is lib/ and a folder or module named
keel in the current directory cannot shadow the package (python3 -m would put the current directory first)."""
import sys

from keel.interfaces.cli import main

if __name__ == "__main__":
    sys.exit(main())
