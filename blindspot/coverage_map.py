"""Which tests execute which lines.

Per-test contexts are what make this affordable: knowing that only 3 of 257
tests touch a changed line means the mutation step re-runs 3 tests, not 257.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

CONFIG = """
[run]
dynamic_context = test_function
branch = False
"""


def run(repo: Path, test_cmd: list[str], data_file: Path) -> dict[str, dict[int, set[str]]]:
    """Run the suite under coverage; return {file: {lineno: {test ids}}}."""
    cfg = repo / ".blindspot.coveragerc"
    cfg.write_text(CONFIG, encoding="utf-8")
    try:
        subprocess.run(
            [test_cmd[0], "-m", "coverage", "run",
             f"--rcfile={cfg}", f"--data-file={data_file}", "-m", *test_cmd[1:]],
            cwd=repo, capture_output=True, text=True, check=False, timeout=900,
        )
        from coverage import CoverageData          # noqa: PLC0415

        data = CoverageData(basename=str(data_file))
        data.read()
        out: dict[str, dict[int, set[str]]] = {}
        for measured in data.measured_files():
            rel = str(Path(measured).resolve())
            per_line: dict[int, set[str]] = {}
            for lineno, contexts in (data.contexts_by_lineno(measured) or {}).items():
                tests = {c for c in contexts if c}
                if tests:
                    per_line[lineno] = tests
            if per_line:
                out[rel] = per_line
        return out
    finally:
        cfg.unlink(missing_ok=True)
