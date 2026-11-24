"""Per-turn play journal for Project D20: one JSON line per completed turn."""

import json
from pathlib import Path


def append_journal_entry(path: Path, record: dict) -> None:
    """Append record as one newline-terminated JSON line to the journal at path.

    Parent directories are created if needed. The record is written verbatim;
    callers must never include secrets or API keys in it.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
