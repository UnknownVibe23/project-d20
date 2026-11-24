"""Tests for d20.llm.prompting. Offline; tmp_path only for injected files."""

import os
from pathlib import Path

import pytest

import d20
from d20.llm.prompting import (
    DEFAULT_GM_PROMPT_PATH,
    build_messages,
    build_state_block,
    load_gm_contract,
)
from d20.state.save import new_game


def _populated_game() -> dict:
    game = new_game("Aria", "A runaway scholar.")
    game["flags"] = {"mood": "wary", "debt": 12, "met_guards": True}
    game["inventory"] = ["rope", "lantern"]
    game["transcript"] = [
        {"role": "player", "text": "I open the door."},
        {"role": "gm", "text": "It creaks open."},
    ]
    return game


def test_load_gm_contract_returns_file_content(tmp_path):
    path = tmp_path / "gm.txt"
    path.write_text("Contract text.\n", encoding="utf-8")
    assert load_gm_contract(path) == "Contract text.\n"


def test_load_gm_contract_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="GM contract file not found"):
        load_gm_contract(tmp_path / "nope.txt")


def test_default_gm_prompt_path_is_repo_root_prompts_gm_txt():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(d20.__file__)))
    assert DEFAULT_GM_PROMPT_PATH == Path(repo_root) / "prompts" / "gm.txt"


def test_default_contract_file_exists_and_starts_the_gm_contract():
    assert load_gm_contract().startswith(
        "You are the Game Master of a solo tabletop RPG session."
    )


def test_build_state_block_populated_game_exact_three_lines():
    game = _populated_game()
    assert build_state_block(game) == (
        "Character: Aria (A runaway scholar.)\n"
        "Flags: debt=12, met_guards=True, mood=wary\n"
        "Inventory: rope, lantern"
    )


def test_build_state_block_without_description_omits_parentheses():
    game = new_game("Aria")
    assert build_state_block(game).splitlines()[0] == "Character: Aria"


def test_build_state_block_empty_flags_and_inventory():
    game = new_game("Aria", "A runaway scholar.")
    assert build_state_block(game) == (
        "Character: Aria (A runaway scholar.)\nFlags: (none)\nInventory: (empty)"
    )


def test_build_state_block_rejects_missing_key():
    game = new_game("Aria")
    del game["flags"]
    with pytest.raises(ValueError, match="missing required key.*flags"):
        build_state_block(game)


def test_build_state_block_rejects_wrong_typed_key():
    game = new_game("Aria")
    game["inventory"] = "rope"
    with pytest.raises(ValueError, match="'inventory' must be a JSON array"):
        build_state_block(game)


def test_build_messages_fresh_game_yields_exactly_system_plus_user():
    game = new_game("Aria")
    messages = build_messages(game, "I look around.")
    assert len(messages) == 2
    assert messages[0] == {"role": "system", "content": load_gm_contract()}
    assert messages[1] == {
        "role": "user",
        "content": (
            "CURRENT FACTS:\n"
            "Character: Aria\nFlags: (none)\nInventory: (empty)"
            "\n\nPLAYER ACTION:\nI look around."
        ),
    }


def test_build_messages_maps_transcript_roles_in_order():
    game = _populated_game()
    messages = build_messages(game, "I attack.")
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[0]["content"] == load_gm_contract()
    assert messages[1] == {"role": "user", "content": "I open the door."}
    assert messages[2] == {"role": "assistant", "content": "It creaks open."}
    final = messages[3]["content"]
    assert final.startswith("CURRENT FACTS:\n")
    assert "Character: Aria (A runaway scholar.)\n" in final
    assert "Flags: debt=12, met_guards=True, mood=wary\n" in final
    assert "Inventory: rope, lantern\n" in final
    assert final.endswith("\n\nPLAYER ACTION:\nI attack.")
