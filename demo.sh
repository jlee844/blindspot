#!/usr/bin/env bash
# Self-contained demo. Builds a throwaway repo with two changes -- one a test
# would catch, one it would not -- runs blindspot, and cleans up after itself.
#
#   ./demo.sh          run it
#   ./demo.sh --slow   pause between steps, for screen recording
set -euo pipefail

SLOW=0; [[ "${1:-}" == "--slow" ]] && SLOW=1
pause() { [[ $SLOW == 1 ]] && sleep "${1:-2.5}" || true; }
say()   { printf '\n\033[1m%s\033[0m\n' "$1"; }

BS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO="$(mktemp -d)"
trap 'rm -rf "$DEMO"' EXIT
cd "$DEMO"

say "A tiny project with a test suite."
mkdir -p pricing tests
cat > pricing/rules.py <<'PY'
def discount(total, member):
    if member and total >= 100:
        return total * 0.9
    return total


def shipping(total):
    if total > 50:
        return 0
    return 5
PY
cat > tests/test_rules.py <<'PY'
from pricing.rules import discount, shipping


def test_members_get_a_discount_over_the_threshold():
    assert discount(200, True) == 180


def test_non_members_pay_full_price():
    assert discount(200, False) == 200


def test_shipping_is_computed():
    assert shipping(10) is not None      # runs it, asserts almost nothing
PY
printf '[tool.pytest.ini_options]\npythonpath = ["."]\n' > pyproject.toml
git init -q . && git add -A && git -c user.email=d@d -c user.name=d commit -qm base
pause

say "Both functions are covered. Coverage says 100%."
python -m pytest -q >/dev/null 2>&1 && echo "  tests pass"
pause

say "Now change one line in each."
python - <<'PY'
import pathlib
p = pathlib.Path("pricing/rules.py"); s = p.read_text()
s = s.replace("if member and total >= 100:", "if member and total >= 120:")
s = s.replace("if total > 50:",              "if total > 60:")
p.write_text(s)
PY
git --no-pager diff --unified=0 -- pricing/rules.py | grep -E '^[+-][^+-]' | sed 's/^/  /'
pause

say "Which of those two would a test actually catch a bug in?"
pause 1.5
PYTHONPATH="$BS" python -m blindspot --tests "pytest -q"
