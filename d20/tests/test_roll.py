"""Tests for the d20.roll CLI. No network; RNG is mocked where needed."""

import sys
from unittest.mock import patch

import pytest

from d20.roll import main


def test_cli_prints_compact_roll_line(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["d20.roll", "2d6+3"])
    with patch("d20.rules.dice._rng") as rng:
        rng.randint.side_effect = [4, 6]
        main()
    assert capsys.readouterr().out == "2d6+3 -> [4, 6] + 3 = 13\n"


def test_cli_invalid_expression_exits_2_with_clean_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["d20.roll", "abc"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: Invalid dice expression 'abc'")


def test_cli_advantage_and_disadvantage_are_mutually_exclusive(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["d20.roll", "d20", "--advantage", "--disadvantage"]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert "mutually exclusive" in capsys.readouterr().err
