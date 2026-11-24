# Changelog
All notable changes. Format based on Keep a Changelog; versioning
SemVer 0.x.

## [Unreleased]
### Added
- Project skeleton, AGENTS.md, PROJECT.md, decisions.md, CI (Task 0)
- Dice module with parser, RollResult, CLI
- Minimal Mistral client (narrate)
- Persistent game-state layer (Task 1-state): `d20/state/save.py` with
  `new_game`/`load_game`/`save_game`, versioned JSON save format v1,
  atomic writes, and `DEFAULT_SAVE_PATH` at `saves/session.json`
