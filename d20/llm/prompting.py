"""Prompt assembly for the narrator loop: GM contract plus per-turn facts."""

import os
from pathlib import Path

import d20
from d20.state.save import _validate_game

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(d20.__file__)))
DEFAULT_GM_PROMPT_PATH = Path(_REPO_ROOT) / "prompts" / "gm.txt"


def load_gm_contract(path: Path = DEFAULT_GM_PROMPT_PATH) -> str:
    """Return the GM contract text stored at path.

    Defaults to the repo-root prompts/gm.txt. Raises FileNotFoundError
    with a readable message if the file is missing.
    """
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"GM contract file not found: {path}") from None


def build_state_block(game: dict) -> str:
    """Render the machine-owned facts of game as three deterministic lines.

    Line 1 is the character (with description in parentheses when set),
    line 2 the flags sorted by key, line 3 the inventory in stored order.
    The transcript is never rendered here. Raises ValueError if game does
    not match the save schema.
    """
    _validate_game(game, context="Invalid game data")
    character = game["character"]
    if character["description"]:
        character_line = f"Character: {character['name']} ({character['description']})"
    else:
        character_line = f"Character: {character['name']}"
    flags = game["flags"]
    if flags:
        flags_line = "Flags: " + ", ".join(
            f"{key}={flags[key]}" for key in sorted(flags)
        )
    else:
        flags_line = "Flags: (none)"
    inventory = game["inventory"]
    if inventory:
        inventory_line = f"Inventory: {', '.join(inventory)}"
    else:
        inventory_line = "Inventory: (empty)"
    return f"{character_line}\n{flags_line}\n{inventory_line}"


def build_messages(game: dict, player_input: str) -> list[dict]:
    """Assemble one turn's full message list for the narrator.

    Message 0 is the system GM contract, then one message per transcript
    entry ("player" -> "user", "gm" -> "assistant"), then the final user
    message with the current facts block and the player's input.
    """
    state_block = build_state_block(game)
    messages = [{"role": "system", "content": load_gm_contract()}]
    for entry in game["transcript"]:
        role = "user" if entry["role"] == "player" else "assistant"
        messages.append({"role": role, "content": entry["text"]})
    messages.append(
        {
            "role": "user",
            "content": (
                f"CURRENT FACTS:\n{state_block}\n\nPLAYER ACTION:\n{player_input}"
            ),
        }
    )
    return messages
