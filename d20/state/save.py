"""Persistent game state for Project D20: one versioned JSON save file.

A solo session is a single dict (see new_game) that save_game writes
atomically and load_game validates in full before returning. stdlib only.
"""

import json
import os
import tempfile
from pathlib import Path

import d20

SAVE_VERSION = 1
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(d20.__file__)))
DEFAULT_SAVE_PATH = Path(_REPO_ROOT) / "saves" / "session.json"

_TOP_LEVEL_KEYS = {"version", "character", "flags", "inventory", "transcript"}
_CHARACTER_KEYS = {"name", "description"}
_TRANSCRIPT_KEYS = {"role", "text"}
_ROLES = ("player", "gm")


def new_game(name: str, description: str = "") -> dict:
    """Return the default save structure for a new character.

    Flags, inventory, and transcript start empty; the narrator loop fills
    the transcript as play proceeds.
    """
    return {
        "version": SAVE_VERSION,
        "character": {"name": name, "description": description},
        "flags": {},
        "inventory": [],
        "transcript": [],
    }


def load_game(path: Path) -> dict:
    """Load and fully validate the save file at path.

    Raises FileNotFoundError if the file is missing. Raises ValueError with
    a readable message if the JSON is invalid, the schema is wrong, or the
    version is unknown. Never returns partially validated data.
    """
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise FileNotFoundError(f"Save file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid save file {path}: not valid JSON ({exc}).") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"Invalid save file {path}: not UTF-8 text ({exc}).") from exc
    _validate_game(data, context=f"Invalid save file {path}")
    return data


def save_game(game: dict, path: Path) -> None:
    """Validate game and atomically write it as JSON to path.

    The dump goes to a temp file in the same directory as path and is then
    moved onto path with os.replace, so a crash mid-save cannot corrupt an
    existing save. Parent directories are created if needed, and no temp
    file remains after a successful save.
    """
    _validate_game(game, context="Invalid game data")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(game, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_game(game, context: str) -> None:
    """Raise ValueError unless game matches the save schema exactly."""
    _require(
        isinstance(game, dict),
        f"{context}: top level must be a JSON object, got {type(game).__name__}.",
    )
    missing = _TOP_LEVEL_KEYS - game.keys()
    _require(
        not missing,
        f"{context}: missing required key(s): {', '.join(sorted(missing))}.",
    )
    extra = set(game.keys()) - _TOP_LEVEL_KEYS
    _require(
        not extra,
        f"{context}: unknown key(s): {', '.join(sorted(extra))}; "
        f"expected exactly {', '.join(sorted(_TOP_LEVEL_KEYS))}.",
    )
    version = game["version"]
    _require(
        not isinstance(version, bool) and isinstance(version, int),
        f"{context}: 'version' must be an integer, got {version!r}.",
    )
    _require(
        version == SAVE_VERSION,
        f"{context}: unknown save version {version}; "
        f"this code supports version {SAVE_VERSION}.",
    )
    character = game["character"]
    _require(
        isinstance(character, dict),
        f"{context}: 'character' must be a JSON object, got {type(character).__name__}.",
    )
    _require(
        set(character.keys()) == _CHARACTER_KEYS,
        f"{context}: 'character' must have exactly the keys "
        f"{', '.join(sorted(_CHARACTER_KEYS))}, got "
        f"{', '.join(sorted(character.keys()))}.",
    )
    _require(
        isinstance(character["name"], str),
        f"{context}: 'character.name' must be a string, got {character['name']!r}.",
    )
    _require(
        isinstance(character["description"], str),
        f"{context}: 'character.description' must be a string, "
        f"got {character['description']!r}.",
    )
    flags = game["flags"]
    _require(
        isinstance(flags, dict),
        f"{context}: 'flags' must be a JSON object, got {type(flags).__name__}.",
    )
    for key, value in flags.items():
        _require(
            isinstance(key, str),
            f"{context}: flag keys must be strings, got {key!r}.",
        )
        _require(
            isinstance(value, (str, bool, int)),
            f"{context}: flag {key!r} must be a string, bool, or int, got {value!r}.",
        )
    inventory = game["inventory"]
    _require(
        isinstance(inventory, list),
        f"{context}: 'inventory' must be a JSON array, got {type(inventory).__name__}.",
    )
    for item in inventory:
        _require(
            isinstance(item, str),
            f"{context}: inventory entries must be strings, got {item!r}.",
        )
    transcript = game["transcript"]
    _require(
        isinstance(transcript, list),
        f"{context}: 'transcript' must be a JSON array, "
        f"got {type(transcript).__name__}.",
    )
    for index, entry in enumerate(transcript):
        _require(
            isinstance(entry, dict),
            f"{context}: transcript entry {index} must be a JSON object, "
            f"got {type(entry).__name__}.",
        )
        _require(
            set(entry.keys()) == _TRANSCRIPT_KEYS,
            f"{context}: transcript entry {index} must have exactly the keys "
            f"{', '.join(sorted(_TRANSCRIPT_KEYS))}, got "
            f"{', '.join(sorted(entry.keys()))}.",
        )
        _require(
            entry["role"] in _ROLES,
            f"{context}: transcript entry {index} has invalid role "
            f"{entry['role']!r}; expected one of "
            f"{', '.join(repr(role) for role in _ROLES)}.",
        )
        _require(
            isinstance(entry["text"], str),
            f"{context}: transcript entry {index} 'text' must be a string, "
            f"got {entry['text']!r}.",
        )
