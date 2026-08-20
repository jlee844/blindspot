"""Diff parsing and mutation. No test runs a suite — that is the CLI's job."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blindspot.diff import parse                    # noqa: E402
from blindspot.mutate import mutate_line            # noqa: E402

DIFF = """diff --git a/x.py b/x.py
--- a/x.py
+++ b/x.py
@@ -1,2 +1,4 @@
 unchanged
+added one
+added two
-removed
"""


def test_only_added_lines_are_reported():
    """A reviewer asks about the lines in front of them, not the whole file."""
    [f] = parse(DIFF)
    assert f.path == "x.py"
    assert f.added == {2, 3}


def test_removed_lines_do_not_shift_the_line_numbers():
    """'-' lines consume no line number in the new file; counting them offsets
    every verdict after the first deletion."""
    [f] = parse(DIFF)
    assert max(f.added) == 3


def test_non_python_files_are_ignored():
    assert parse(DIFF.replace("x.py", "x.md")) == []


def test_a_file_with_no_added_lines_is_dropped_by_identity_not_truthiness():
    """FileDiff defines __len__, so `if cur:` on a fresh one is False and the
    file is silently dropped before its hunks are read."""
    only_removals = DIFF.replace("+added one\n", "").replace("+added two\n", "")
    assert parse(only_removals) == []
    assert parse(DIFF) != []


SRC = [
    "def check(a, b):\n",
    "    if a == b:\n",
    "        return True\n",
    "    limit = 40\n",
    "    if a and b:\n",
    '    msg = "a == b"\n',
    "    # a == b\n",
    "    import os\n",
]


@pytest.mark.parametrize("lineno,expected", [
    (2, "== -> !="),
    (3, "True -> False"),
    (4, "40 -> 41"),
    (5, "and -> or"),
])
def test_logic_is_mutated(lineno, expected):
    m = mutate_line(SRC, lineno)
    assert m is not None and m.rule == expected


@pytest.mark.parametrize("lineno", [1, 6, 7, 8])
def test_non_logic_is_left_alone(lineno):
    """Strings, comments, imports and defs prove nothing when broken."""
    assert mutate_line(SRC, lineno) is None


def test_any_integer_is_mutable_not_just_zero_and_one():
    """An arbitrary cap (40 files, 80 chars, 25 turns) is exactly the constant
    an agent picks freely and no test pins down."""
    assert mutate_line(["def f():\n", "    x = items[:80]\n"], 2).rule == "80 -> 81"


def test_a_mutation_that_breaks_syntax_is_discarded():
    m = mutate_line(["def f():\n", "    return 1\n"], 2)
    assert m is None or "def" not in m.after


def test_parseability_is_judged_against_the_original_not_absolutely():
    """A bare indented line never parses on its own. Judging mutations against
    an absolute check discards every one of them and the tool reports nothing."""
    assert mutate_line(["    if a == b:\n"], 1) is not None


def test_a_line_out_of_range_returns_none():
    assert mutate_line(SRC, 999) is None
    assert mutate_line(SRC, 0) is None


def test_the_readme_does_not_hardcode_a_test_count():
    """The count went stale in a sibling repo twice; the badge is CI's job now."""
    import re
    from pathlib import Path
    readme = Path(__file__).resolve().parent.parent.joinpath("README.md").read_text(encoding="utf-8")
    # blindspot's own example output legitimately says "(3 tests touch it)" --
    # strip fenced code blocks and check only the prose.
    prose = re.sub(r"```.*?```", "", readme, flags=re.S)
    stale = re.findall(r"\b\d+\s*tests\b", prose)
    assert not stale, f"hardcoded test counts in the README: {stale}"
