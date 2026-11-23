"""Tests for d20.rules.dice. Exact assertions use a mocked RNG."""

from unittest.mock import patch

import pytest

from d20.rules.dice import RollResult, roll


class _StubRNG:
    def __init__(self, values):
        self._values = iter(values)

    def randint(self, low, high):
        return next(self._values)


def _patched_roll(expression, mode, values):
    with patch("d20.rules.dice._rng", _StubRNG(values)):
        return roll(expression, mode)


def test_single_d20_total():
    result = _patched_roll("d20", "normal", [15])
    assert isinstance(result, RollResult)
    assert result.expression == "d20"
    assert result.mode == "normal"
    assert result.rolls == [15]
    assert result.kept == [15]
    assert result.modifier == 0
    assert result.total == 15


def test_2d6_plus_3_total():
    result = _patched_roll("2d6+3", "normal", [4, 6])
    assert result.rolls == [4, 6]
    assert result.kept == [4, 6]
    assert result.modifier == 3
    assert result.total == 13


def test_negative_modifier():
    result = _patched_roll("3d8-1", "normal", [8, 8, 8])
    assert result.modifier == -1
    assert result.total == 23


def test_zero_modifier():
    result = _patched_roll("4d6+0", "normal", [1, 2, 3, 4])
    assert result.modifier == 0
    assert result.total == 10


def test_repeated_rolls_differ_with_real_rng():
    outcomes = {roll("d20").total for _ in range(25)}
    assert len(outcomes) > 1


def test_advantage_keeps_higher():
    result = _patched_roll("d20", "advantage", [5, 17])
    assert result.rolls == [5, 17]
    assert result.kept == [17]
    assert result.total == 17


def test_disadvantage_keeps_lower():
    result = _patched_roll("d20", "disadvantage", [5, 17])
    assert result.rolls == [5, 17]
    assert result.kept == [5]
    assert result.total == 5


def test_advantage_with_modifier():
    result = _patched_roll("d20+5", "advantage", [3, 9])
    assert result.kept == [9]
    assert result.modifier == 5
    assert result.total == 14


@pytest.mark.parametrize("expression", ["2d20", "3d20", "d6", "2d6+3"])
def test_advantage_modes_require_single_d20(expression):
    with pytest.raises(ValueError):
        roll(expression, "advantage")
    with pytest.raises(ValueError):
        roll(expression, "disadvantage")


@pytest.mark.parametrize(
    "expression", ["abc", "2d", "d6d6", "", "2d6+3+4", "0d6", "d0", "1.5d6"]
)
def test_invalid_expressions_raise_value_error(expression):
    with pytest.raises(ValueError):
        roll(expression)


def test_invalid_mode_raises_value_error():
    with pytest.raises(ValueError):
        roll("d20", mode="wild")


def test_str_matches_cli_example_format():
    result = _patched_roll("2d6+3", "normal", [4, 6])
    assert str(result) == "2d6+3 -> [4, 6] + 3 = 13"
