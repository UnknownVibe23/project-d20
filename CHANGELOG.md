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
- GM contract stored verbatim as `prompts/gm.txt`; prompt builder
  `d20/llm/prompting.py` with `load_gm_contract`, `build_state_block`,
  `build_messages` (Task 2-gm-contract)
- `narrate_messages(messages)` in the Mistral client with offline
  validation; `narrate()` is now a thin wrapper over it using the GM
  contract, and `StubLLM` gained `narrate_messages` (Task 2-gm-contract)
