"""Tests for d20.state.save. tmp_path only; no network, no repo-root writes."""

import json
import os
from pathlib import Path

import pytest

import d20
from d20.state.save import (
    DEFAULT_SAVE_PATH,
    SAVE_VERSION,
    load_game,
    new_game,
    save_game,
)


def _game_with_content() -> dict:
    game = new_game("Aria", description="A runaway scholar.")
    game["flags"] = {"met_guards": True, "debt": 12, "mood": "wary"}
    game["inventory"] = ["rope", "lantern"]
    game["transcript"] = [
        {"role": "player", "text": "I open the door."},
        {"role": "gm", "text": "It creaks open."},
    ]
    return game


def test_new_game_returns_exactly_the_documented_default_structure():
    assert new_game("Aria") == {
        "version": SAVE_VERSION,
        "character": {"name": "Aria", "description": ""},
        "flags": {},
        "inventory": [],
        "transcript": [],
    }
    assert new_game("Aria", "A runaway scholar.") == {
        "version": 1,
        "character": {"name": "Aria", "description": "A runaway scholar."},
        "flags": {},
        "inventory": [],
        "transcript": [],
    }


def test_round_trip_empty_game(tmp_path):
    path = tmp_path / "session.json"
    game = new_game("Aria")
    save_game(game, path)
    assert load_game(path) == game


def test_round_trip_populated_game(tmp_path):
    path = tmp_path / "session.json"
    game = _game_with_content()
    save_game(game, path)
    assert load_game(path) == game


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "deeper" / "session.json"
    save_game(new_game("Aria"), path)
    assert load_game(path) == new_game("Aria")


def test_atomic_overwrite_replaces_existing_save_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "session.json"
    save_game(new_game("Aria"), path)
    updated = _game_with_content()
    save_game(updated, path)
    assert load_game(path) == updated
    assert [p.name for p in tmp_path.iterdir()] == ["session.json"]


def test_temp_file_is_created_in_the_same_directory_as_the_target(
    tmp_path, monkeypatch
):
    path = tmp_path / "session.json"
    seen = {}
    real_replace = os.replace

    def spy_replace(src, dst):
        seen["src_parent"] = Path(src).parent
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy_replace)
    save_game(new_game("Aria"), path)
    assert seen["src_parent"] == tmp_path


def test_invalid_input_never_touches_an_existing_save(tmp_path):
    path = tmp_path / "session.json"
    original = new_game("Aria")
    save_game(original, path)
    broken = _game_with_content()
    broken["version"] = 99
    with pytest.raises(ValueError, match="unknown save version"):
        save_game(broken, path)
    assert load_game(path) == original
    assert [p.name for p in tmp_path.iterdir()] == ["session.json"]


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="Save file not found"):
        load_game(tmp_path / "nope.json")


def test_corrupt_json_raises_value_error(tmp_path):
    path = tmp_path / "session.json"
    path.write_bytes(b"{not json at all")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_game(path)


def test_unknown_version_raises_value_error(tmp_path):
    path = tmp_path / "session.json"
    game = new_game("Aria")
    game["version"] = 2
    path.write_text(json.dumps(game), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown save version 2"):
        load_game(path)


@pytest.mark.parametrize(
    "missing_key", ["version", "character", "flags", "inventory", "transcript"]
)
def test_missing_top_level_key_raises_value_error(tmp_path, missing_key):
    path = tmp_path / "session.json"
    game = new_game("Aria")
    del game[missing_key]
    path.write_text(json.dumps(game), encoding="utf-8")
    with pytest.raises(ValueError, match=f"missing required key.*{missing_key}"):
        load_game(path)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda g: g.update(flags=["not", "an", "object"]),
        lambda g: g.update(inventory="rope"),
        lambda g: g.update(transcript={"role": "player"}),
        lambda g: g["character"].update(name=42),
        lambda g: g["character"].update(description=None),
        lambda g: g.update(version="1"),
        lambda g: g.update(version=True),
        lambda g: g["flags"].update(mood=2.5),
        lambda g: g["inventory"].append(7),
    ],
)
def test_wrong_typed_key_raises_value_error(tmp_path, mutation):
    path = tmp_path / "session.json"
    game = _game_with_content()
    mutation(game)
    path.write_text(json.dumps(game), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid save file"):
        load_game(path)


def test_unknown_top_level_key_raises_value_error(tmp_path):
    path = tmp_path / "session.json"
    game = new_game("Aria")
    game["extra"] = True
    path.write_text(json.dumps(game), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown key"):
        load_game(path)


@pytest.mark.parametrize(
    "entry",
    [
        {"role": "npc", "text": "hi"},
        {"role": "player"},
        {"text": "hi"},
        {"role": "player", "text": 3},
        {"role": "gm", "text": "hi", "extra": 1},
        "not an object",
    ],
)
def test_bad_transcript_entry_raises_value_error(tmp_path, entry):
    path = tmp_path / "session.json"
    game = new_game("Aria")
    game["transcript"] = [entry]
    path.write_text(json.dumps(game), encoding="utf-8")
    with pytest.raises(ValueError, match="transcript entry 0"):
        load_game(path)


def test_save_game_rejects_invalid_input_before_writing(tmp_path):
    path = tmp_path / "session.json"
    with pytest.raises(ValueError, match="Invalid game data"):
        save_game({"version": 1}, path)
    assert not path.exists()
    assert list(tmp_path.iterdir()) == []


def test_default_save_path_is_repo_root_saves_session_json():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(d20.__file__)))
    assert DEFAULT_SAVE_PATH == Path(repo_root) / "saves" / "session.json"
