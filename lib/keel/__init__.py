"""keel core package (System-ADR 0020).

Layers, each importing only from the ones before it: domain, store, integrations, services, interfaces.
Standard library only; Python 3.9 or newer.
"""
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("keel: Python 3.9 oder neuer wird gebraucht, gefunden %d.%d\n" % sys.version_info[:2])
    raise SystemExit(2)

__version__ = "0.20.2"
