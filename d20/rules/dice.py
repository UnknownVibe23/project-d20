"""Dice rolling for Project D20.

The RNG is random.SystemRandom at module level: it draws from OS entropy
instead of a seeded PRNG, because dice results are live game state, not a
reproducible simulation, and a predictable PRNG would let rolls be
guessed.
"""

import random
import re
from dataclasses import dataclass

_rng = random.SystemRandom()

_EXPRESSION = re.compile(r"^(\d*)d(\d+)(?:([+-])(\d+))?$", re.IGNORECASE)
_MAX_DICE = 100
_MODES = ("normal", "advantage", "disadvantage")


@dataclass
class RollResult:
    """Outcome of one roll() call."""

    expression: str
    mode: str
    rolls: list[int]
    kept: list[int]
    modifier: int
    total: int

    def __str__(self) -> str:
        """Compact one-line summary, e.g. '2d6+3 -> [4, 6] + 3 = 13'."""
        sign = "+" if self.modifier >= 0 else "-"
        head = (
            f"{self.expression} ({self.mode})"
            if self.mode != "normal"
            else self.expression
        )
        kept = f" kept {self.kept}" if self.mode != "normal" else ""
        return (
            f"{head} -> {self.rolls}{kept} {sign} {abs(self.modifier)} = {self.total}"
        )


def roll(expression: str, mode: str = "normal") -> RollResult:
    """Roll the dice described by expression and return a RollResult.

    Supported expressions: 'd20', '2d6+3', '3d8-1', '4d6' (count defaults
    to 1, modifier defaults to 0). mode is 'normal', 'advantage', or
    'disadvantage'; the latter two roll two d20 and keep the higher or
    lower, and are only valid with a single d20. Invalid input raises
    ValueError with a human-readable message.
    """
    if mode not in _MODES:
        raise ValueError(
            f"Invalid mode {mode!r}; expected one of {', '.join(repr(m) for m in _MODES)}."
        )
    match = _EXPRESSION.match(expression.strip().lower())
    if not match:
        raise ValueError(
            f"Invalid dice expression {expression!r}; "
            "expected forms like 'd20', '2d6+3', '3d8-1'."
        )
    count_text, sides_text, sign, mod_text = match.groups()
    count = int(count_text) if count_text else 1
    sides = int(sides_text)
    modifier = int(mod_text) if mod_text else 0
    if sign == "-":
        modifier = -modifier
    if not 1 <= count <= _MAX_DICE:
        raise ValueError(f"Invalid dice count in {expression!r}; use 1 to {_MAX_DICE}.")
    if sides < 1:
        raise ValueError(
            f"Invalid die size in {expression!r}; sides must be at least 1."
        )
    if mode != "normal" and (count != 1 or sides != 20):
        raise ValueError(
            f"Mode {mode!r} is only valid with a single d20, got {expression!r}."
        )
    rolls = [_rng.randint(1, sides) for _ in range(2 if mode != "normal" else count)]
    if mode == "advantage":
        kept = [max(rolls)]
    elif mode == "disadvantage":
        kept = [min(rolls)]
    else:
        kept = list(rolls)
    return RollResult(
        expression=expression.strip().lower(),
        mode=mode,
        rolls=rolls,
        kept=kept,
        modifier=modifier,
        total=sum(kept) + modifier,
    )
