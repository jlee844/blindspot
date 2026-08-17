"""Break a line on purpose. See whether any test notices.

This is the whole point of the tool. Coverage says a line *ran*. It does not
say a test would fail if the line were wrong — and a line that runs while
nothing asserts on it is exactly the line an agent gets away with.

Mutations are textual and conservative: each must leave the file parseable,
and anything that doesn't is discarded rather than reported as a result.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

# Ordered: the first applicable mutation wins, so a line gets one clear edit.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![=!<>])==(?!=)"), "!="),
    (re.compile(r"!="), "=="),
    (re.compile(r"(?<![<>])<=(?!=)"), ">"),
    (re.compile(r"(?<![<>])>=(?!=)"), "<"),
    (re.compile(r"\bis not\b"), "is"),
    (re.compile(r"\bnot in\b"), "in"),
    (re.compile(r"\bTrue\b"), "False"),
    (re.compile(r"\bFalse\b"), "True"),
    (re.compile(r"\band\b"), "or"),
    (re.compile(r"\bor\b"), "and"),
    # Any integer literal, not just 0/1: a slice cap of 40 or a window of 25
    # is exactly the kind of constant an agent picks arbitrarily and no test
    # pins down. Handled below, since the replacement depends on the match.
    (re.compile(r"(?<![\w.])\d+(?![\w.])"), "__INCR__"),
]

# Lines where a mutation proves nothing about the change under review.
_SKIP = re.compile(r"^\s*($|#|\"\"\"|'''|import |from .+ import|@|"
                   r"(class|def) |else\s*:|try\s*:|pass\b)")


@dataclass(frozen=True)
class Mutation:
    lineno: int
    before: str
    after: str
    rule: str


def mutate_line(source_lines: list[str], lineno: int) -> Mutation | None:
    """One conservative edit to line `lineno` (1-based), or None."""
    if not (1 <= lineno <= len(source_lines)):
        return None
    original = source_lines[lineno - 1]
    if _SKIP.match(original):
        return None
    # Strings and comments are not logic; mutating them proves nothing.
    code = re.sub(r"(\"[^\"]*\"|'[^']*'|#.*$)", lambda m: " " * len(m.group(0)), original)
    # Only reject a mutation for breaking syntax the ORIGINAL had. Parsing a
    # bare indented line always raises IndentationError, so an absolute check
    # silently discards every mutation and the tool reports nothing, forever.
    def _parses(lines: list[str]) -> bool:
        try:
            ast.parse("".join(lines))
            return True
        except SyntaxError:
            return False

    baseline_ok = _parses(source_lines)

    for pattern, replacement in _RULES:
        m = pattern.search(code)
        if not m:
            continue
        repl = replacement
        if repl == "__INCR__":
            repl = str(int(m.group(0)) + 1)
        mutated = original[:m.start()] + repl + original[m.end():]
        candidate = list(source_lines)
        candidate[lineno - 1] = mutated
        if baseline_ok and not _parses(candidate):
            continue                      # the mutation broke it; discard
        return Mutation(lineno, original.rstrip("\n"), mutated.rstrip("\n"),
                        f"{m.group(0)} -> {repl}")
    return None
