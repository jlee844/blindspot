"""Which lines did this change touch?

Only added and modified lines matter. A reviewer is not asking whether the
whole file is tested — they are asking about the lines in front of them.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass
class FileDiff:
    path: str
    added: set[int] = field(default_factory=set)

    def __len__(self) -> int:
        return len(self.added)


def parse(diff_text: str, include: tuple[str, ...] = (".py",)) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    lineno = 0
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            p = line[4:].strip()
            p = p[2:] if p.startswith("b/") else p
            cur = FileDiff(p) if p.endswith(include) else None
            # `if cur:` is FALSE here: FileDiff defines __len__, and a fresh
            # one has no added lines yet, so truthiness says "empty" and the
            # file is silently dropped. Identity check, not truthiness.
            if cur is not None:
                files.append(cur)
            continue
        if cur is None:
            continue
        m = _HUNK.match(line)
        if m:
            lineno = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            cur.added.add(lineno)
            lineno += 1
        elif line.startswith(" "):
            lineno += 1
        # "-" lines consume no line number in the new file

    return [f for f in files if f.added]


def from_git(repo: Path, rev: str | None = None) -> list[FileDiff]:
    """Working-tree changes by default; `rev` compares against a ref."""
    cmd = ["git", "-C", str(repo), "diff", "--unified=0", "--no-color"]
    if rev:
        cmd.append(rev)
    else:
        cmd.append("HEAD")
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return parse(out.stdout)
