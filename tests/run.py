"""Runs the unit and contract tests across worker processes, standard library only.

Every test method is one job on a shared queue, so a slow module does not hold up a worker while the others idle.
Contract tests work in their own temp folders and metrics roots, so they can run side by side.

  python3 tests/run.py            # workers = CPU count, at most 8
  python3 tests/run.py -j 3       # GitHub runner
  python3 tests/run.py -j 1 -v    # sequential, every test name
"""
import argparse
import io
import multiprocessing
import os
import sys
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (start dir, top-level dir) as unittest discover gets them in the README
SUITES = [("tests/unit", "."), ("tests/contract", "tests/contract")]


def _setup_path():
    for _, top in SUITES:
        p = os.path.join(REPO, top)
        if p not in sys.path:
            sys.path.insert(0, p)


def _ids(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from _ids(t)
        else:
            yield t.id()


def _discover():
    _setup_path()
    loader = unittest.TestLoader()
    ids = []
    for start, top in SUITES:
        suite = loader.discover(os.path.join(REPO, start), top_level_dir=os.path.join(REPO, top))
        if loader.errors:
            sys.exit("".join(loader.errors))
        ids.extend(_ids(suite))
    return ids


def _run(test_id):
    """One test in a worker: (id, outcome, seconds, report)."""
    out = io.StringIO()
    start = time.time()
    result = unittest.TextTestRunner(stream=out, verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName(test_id))
    if result.failures or result.errors or result.unexpectedSuccesses:
        outcome = "FAIL"
    elif result.skipped:
        outcome = "skip"
    else:
        outcome = "ok"
    return test_id, outcome, time.time() - start, out.getvalue() if outcome == "FAIL" else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-j", "--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    os.chdir(REPO)
    ids = _discover()
    start = time.time()
    # spawn, not fork: a forked worker inherits the harness temp folder of the parent, and all workers would build
    # the same fixture in it at once (Linux forks by default, macOS spawns).
    with multiprocessing.get_context("spawn").Pool(max(args.jobs, 1), initializer=_setup_path) as pool:
        results = []
        for r in pool.imap_unordered(_run, ids):
            results.append(r)
            if args.verbose:
                print(f"{r[1]:4} {r[2]:5.1f}s {r[0]}", flush=True)
            elif r[1] == "FAIL":
                print(f"FAIL {r[0]}", flush=True)

    failed = [r for r in results if r[1] == "FAIL"]
    for r in failed:
        print("=" * 70 + f"\n{r[0]}\n{r[3]}")
    skipped = sum(r[1] == "skip" for r in results)
    print(f"{len(results)} tests, {len(failed)} failed, {skipped} skipped, "
          f"{time.time() - start:.1f}s with {args.jobs} workers")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
