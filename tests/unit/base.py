"""Shared setup for the unit tests of lib/keel: the package on sys.path, a private metrics root per test."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIB = str(REPO / "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)


class TempTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="keel-unit-")).resolve()
        self._old = os.environ.get("KEEL_METRICS_DIR")
        os.environ["KEEL_METRICS_DIR"] = str(self.tmp / "metrics")

    def tearDown(self):
        if self._old is None:
            os.environ.pop("KEEL_METRICS_DIR", None)
        else:
            os.environ["KEEL_METRICS_DIR"] = self._old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def env(self):
        return {**os.environ, "PYTHONPATH": LIB}
