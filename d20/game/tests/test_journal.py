"""Tests for d20.game.journal. tmp_path only; no network, no repo writes."""

import json

from d20.game.journal import append_journal_entry


def test_append_creates_parent_dirs_and_writes_one_newline_terminated_line(tmp_path):
    path = tmp_path / "deep" / "nested" / "play.jsonl"
    record = {
        "ts": "2026-11-24T14:00:00+00:00",
        "turn": 1,
        "player_input": "I look around.",
        "prompt_chars": 120,
        "reply_chars": 42,
        "model": None,
    }
    append_journal_entry(path, record)
    raw = path.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    assert raw.count("\n") == 1
    assert json.loads(raw) == record


def test_append_twice_appends_two_lines_in_order(tmp_path):
    path = tmp_path / "play.jsonl"
    append_journal_entry(path, {"turn": 1, "player_input": "one"})
    append_journal_entry(path, {"turn": 2, "player_input": "two"})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["turn"] for line in lines] == [1, 2]
    assert [json.loads(line)["player_input"] for line in lines] == ["one", "two"]


def test_record_is_written_verbatim_without_added_or_dropped_fields(tmp_path):
    path = tmp_path / "play.jsonl"
    record = {"turn": 7, "note": "no secrets here"}
    append_journal_entry(path, record)
    assert json.loads(path.read_text(encoding="utf-8")) == record
