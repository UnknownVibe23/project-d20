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
- Narrator game loop `d20/game/session.py` with `GameSession`: input ->
  prompt assembly -> LLM -> transcript -> autosave -> journal entry,
  local slash commands (/help, /quit, /take, /drop, /flag, /stats), and
  atomic turns (an LLM failure commits nothing) (Task 3-narrator-loop)
- Play journal `d20/game/journal.py` with `append_journal_entry`: one
  newline-terminated JSON line per completed turn (ts, turn,
  player_input, prompt_chars, reply_chars, model) (Task 3-narrator-loop)
- CLI `python -m d20.play` (`d20/play.py`): --new/--description/--save/
  --journal flags, exit code 2 on expected errors, exit code 1 with a
  one-line error on LLM/network failures mid-session (Task 3-narrator-loop)

### Fixed
- Narrator client (`d20/llm/client.py`): the HTTP timeout now comes from
  the `MISTRAL_TIMEOUT` env var (default 120s, real env wins over `.env`),
  and the reply is extracted by `_extract_reply`, which accepts both a
  plain-string `content` and a list of typed blocks (concatenating the
  `text` fields of `type == "text"` blocks) and raises a readable
  `ValueError` naming the `finish_reason` when the reply contains no text
  (Task P1-F1)
