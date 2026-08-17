"""Which lines in this change would a test actually catch a bug in?

Coverage tells you a line ran. It does not tell you anything asserted on it —
and a line that runs while nothing checks it is exactly the line an agent gets
away with. This mutates each changed line and re-runs only the tests that
touch it. A line is verified only when a test actually fails.
"""

from .diff import FileDiff, from_git, parse
from .mutate import Mutation, mutate_line
from .run import EXECUTED, GUARDED, SKIPPED, UNCOVERED, LineVerdict, analyse

__all__ = ["FileDiff", "from_git", "parse", "Mutation", "mutate_line",
           "analyse", "LineVerdict", "GUARDED", "EXECUTED", "UNCOVERED", "SKIPPED"]
__version__ = "0.1.0"
