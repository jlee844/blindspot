"""Verdict per changed line: would a test notice if this were wrong?"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .coverage_map import run as run_coverage
from .diff import FileDiff
from .mutate import Mutation, mutate_line

GUARDED, EXECUTED, UNCOVERED, SKIPPED = "guarded", "executed", "uncovered", "skipped"


@dataclass
class LineVerdict:
    path: str
    lineno: int
    status: str
    tests: int = 0
    mutation: Mutation | None = None
    detail: str = ""


def _run_tests(repo: Path, python: str, k_expr: str) -> bool:
    """True if the suite PASSED — i.e. nothing noticed the mutation."""
    r = subprocess.run([python, "-m", "pytest", "-x", "-q", "-k", k_expr],
                       cwd=repo, capture_output=True, text=True, timeout=600)
    return r.returncode == 0


def _test_names(contexts: set[str]) -> list[str]:
    """coverage's dynamic contexts are 'module.test_function', NOT pytest node
    ids — a '::' filter matches nothing and every line reports as unguarded."""
    out = set()
    for c in contexts:
        name = c.split("|")[0].rsplit(".", 1)[-1]
        if name.startswith("test"):
            out.add(name)
    return sorted(out)[:8]               # 8 tests is plenty of signal


def analyse(repo: Path, files: list[FileDiff], python: str,
            test_cmd: list[str]) -> list[LineVerdict]:
    with tempfile.TemporaryDirectory() as td:
        cov = run_coverage(repo, [python, *test_cmd], Path(td) / "cov.db")

    verdicts: list[LineVerdict] = []
    for fd in files:
        target = (repo / fd.path).resolve()
        if not target.exists():
            continue
        per_line = cov.get(str(target), {})
        source = target.read_text(encoding="utf-8").splitlines(keepends=True)
        original = "".join(source)

        for lineno in sorted(fd.added):
            contexts = per_line.get(lineno, set())
            if not contexts:
                verdicts.append(LineVerdict(fd.path, lineno, UNCOVERED))
                continue
            mut = mutate_line(source, lineno)
            if mut is None:
                verdicts.append(LineVerdict(fd.path, lineno, SKIPPED,
                                            len(contexts),
                                            detail="nothing meaningful to break"))
                continue
            tests = _test_names(contexts)
            if not tests:
                verdicts.append(LineVerdict(fd.path, lineno, EXECUTED, len(contexts),
                                            mut, "covered, but no test id recorded"))
                continue

            patched = list(source)
            patched[lineno - 1] = mut.after + "\n"
            try:
                target.write_text("".join(patched), encoding="utf-8")
                survived = _run_tests(repo, python, " or ".join(tests))
            finally:
                target.write_text(original, encoding="utf-8")   # always restore

            verdicts.append(LineVerdict(
                fd.path, lineno, EXECUTED if survived else GUARDED,
                len(contexts), mut,
                "no test failed when broken" if survived
                else f"caught by {len(tests)} test(s)"))
    return verdicts
