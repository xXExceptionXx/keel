"""Single entry point of the scripts into the keel package: makes lib/ importable (System-ADR 0020).

Scripts run as `python3 scripts/<name>.py`, so scripts/ is already on sys.path and `import _keel` works.
"""
import sys
from pathlib import Path

LIB = str(Path(__file__).resolve().parent.parent / "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
