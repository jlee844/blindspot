"""blindspot — which changed lines would a test actually catch a bug in?

    python -m blindspot                      # working tree vs HEAD
    python -m blindspot --rev main           # a branch
    python -m blindspot --tests tests/unit   # narrow the suite
"""
from __future__ import annotations

import argparse
import collections
import json
import shlex
import sys
from pathlib import Path

from .diff import from_git
from .run import EXECUTED, GUARDED, SKIPPED, UNCOVERED, analyse

TAG = {GUARDED: "GUARDED ", EXECUTED: "BLIND   ",
       UNCOVERED: "UNTESTED", SKIPPED: "n/a     "}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="blindspot")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--rev", default=None, help="compare against this ref")
    ap.add_argument("--python", default=sys.executable)
    # One string, not nargs="*": argparse stops consuming at the first token
    # that looks like a flag, so `--tests pytest -q x.py` loses "-q x.py".
    ap.add_argument("--tests", default="pytest -q",
                    help='test command, quoted (default: "pytest -q")')
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-blind", action="store_true",
                    help="exit 1 if any changed line runs unasserted (for CI)")
    a = ap.parse_args(argv)

    repo = Path(a.repo).resolve()
    files = from_git(repo, a.rev)
    if not files:
        print("  no changed Python lines")
        return 0

    verdicts = analyse(repo, files, a.python, shlex.split(a.tests))
    counts = collections.Counter(v.status for v in verdicts)

    if a.json:
        json.dump([{"path": v.path, "line": v.lineno, "status": v.status,
                    "tests": v.tests, "detail": v.detail,
                    "mutation": v.mutation.rule if v.mutation else None}
                   for v in verdicts], sys.stdout, indent=2)
        print()
    else:
        total = len(verdicts)
        print(f"\n  {total} changed lines\n")
        for v in verdicts:
            if v.status == SKIPPED:
                continue
            print(f"  {TAG[v.status]} {v.path}:{v.lineno}   ({v.tests} tests touch it)")
            if v.mutation:
                print(f"           changed {v.mutation.rule:<14} {v.detail}")
        print(f"\n  guarded {counts[GUARDED]} · blind {counts[EXECUTED]} · "
              f"untested {counts[UNCOVERED]} · n/a {counts[SKIPPED]}")
        if counts[EXECUTED]:
            print(f"\n  {counts[EXECUTED]} line(s) ran during the tests and nothing "
                  f"failed when broken.\n  Coverage would call these covered.")

    return 1 if (a.fail_on_blind and counts[EXECUTED]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
