# decisions.md — implementation decision log

Append-only. coding-agent entries are proposed by the coding AI and
accepted by the human at merge.

## D-001 — Workflow adopted: per-task-card branches/PRs, AGENTS.md+PROJECT.md context, CI from start — 2026-11-23
Context: solo project, one human supervisor, all code written by AI agents.
Decision: per-task-card branches and PRs; rules in AGENTS.md; status in
PROJECT.md; pytest+ruff CI from Task 0.
Alternatives: single evergreen PR (rejected: unreviewable diffs);
CONTRIBUTING.md (rejected: human convention, agents read AGENTS.md).
Decided-by: planner
Status: Accepted in PR #1

## D-002 — Bootstrap of main branch: human creates it, no AI exceptions — 2026-11-23
Context: empty repo had no main to open PR #1 against; coder asked
whether pushing an empty orphan main was acceptable.
Decision: human created main once via the GitHub UI; never-push-main
rule holds with zero exceptions.
Alternatives: AI push of empty orphan main (rejected: the rule admits
no exceptions); leaving task/0-skeleton as default branch (rejected:
inverts the review flow).
Decided-by: planner
Status: Accepted in PR #2

## D-003 — Accepted Task 0 deviations and CLI polish — 2026-11-23
Context: review flagged implementation choices beyond the card spec.
Decision: accepted: modifier with single-d20 advantage/disadvantage
(d20+5), dice count cap 100, adv/dis output format, .env anchored to
repo root, clean CLI error handling.
Alternatives: strict bare d20 only for adv/dis (rejected: needless
strictness); traceback on CLI input errors (rejected: bad UX).
Decided-by: planner
Status: Accepted in PR #2

## D-004 — State-layer internals: strict schema, temp-file discipline, error wording — 2026-11-24
Context: card 1-state fixed the save format and public API but not the validation internals or error text.
Decision: schema enforced strictly (exactly the five top-level keys, no extras; transcript entries exactly role+text); save_game validates before writing, then dumps to a hidden mkstemp temp file in the target directory, fsyncs, and os.replace's it (temp removed on failure); ValueError messages carry the file path; DEFAULT_SAVE_PATH anchored to repo root like the .env loader; str paths accepted alongside Path.
Alternatives: lenient extra keys (rejected: card says "exactly these five"); temp file in the system temp dir (rejected: os.replace across filesystems is not atomic); plain open+write (rejected: not crash-safe).
Decided-by: coding-agent
Status: Accepted in PR #3

## D-005 — Prompt-builder internals: validator reuse, flag rendering, stub shape — 2026-11-24
Context: card 2-gm-contract fixed the API and line formats but not validator reuse, value rendering, or StubLLM internals.
Decision: `build_state_block` reuses d20.state.save's private `_validate_game` (card 1 files untouched); flag values render via Python `str()`, so bools appear as `True`/`False`; `build_messages` loads the contract from `DEFAULT_GM_PROMPT_PATH`; StubLLM records `narrate_messages` calls in a separate `.messages` list with its own reply rotation; a local `_require` helper in client.py keeps the mandated ValueError raises without tripping ruff TRY004; `prompts/gm.txt` ends with a single trailing newline.
Alternatives: making save.py's validator public (rejected: card 2 must not modify card 1 files); JSON-style `true`/`false` in the facts block (rejected: plain `str()` is deterministic and the block is read by the LLM, not parsed); one shared rotation counter in StubLLM (rejected: would change existing narrate test semantics).
Decided-by: coding-agent
Status: Proposed in PR for task/2-gm-contract (pending human acceptance at merge)
