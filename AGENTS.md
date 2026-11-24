# AGENTS.md — Project D20 development rules

Read this file, PROJECT.md, and decisions.md at the start of every
session, in full.

## Mission
Project D20, a personal AI Game Master: deterministic Python code owns
all rules and state; the LLM narrates only. Solo play. English. Rules
authority: D&D SRD 5.2 (CC-BY-4.0).

## Git and workflow
- One branch per task card, named task/<card-id>, e.g. task/0-skeleton.
- NEVER commit to or push main. NEVER merge, approve, or close PRs.
  Only the human merges.
- NEVER force-push or rewrite published history. No destructive git
  commands.
- One PR per task card. The PR body must contain four sections:
  1. What was implemented
  2. Deviations from the task card and why
  3. New decisions.md entries added by this PR
  4. Open questions for the human
- Small, conventional commits, each referencing the task card id.
- Run pytest and ruff locally before every push. CI (pytest + ruff)
  must pass before the human can merge.

## Scope discipline
- Implement exactly what the task card specifies. Nothing extra.
- No drive-by refactors or reformatting of files a task did not touch.
- No new dependencies unless the task card says so.
- If the spec is ambiguous or you are blocked: STOP. Write the open
  question into the PR body. Do not guess. This rule overrides all
  productivity instincts.
- After each task: summarize every file in one sentence for the
  human review. The human never merges code they cannot explain.

## Tests
- Every change ships with its tests. Tests for pure logic use a
  mocked/seeded RNG for exact assertions.
- No test ever performs network access or calls the real Mistral
  API. Use the StubLLM fixture in d20/llm/client.py tests.
- Never run tests against real campaign data; use temp databases
  and temp directories.

## Secrets and data
- Secrets live only in .env (gitignored). Never commit, print, or
  log secrets or API keys.
- .env.example documents every required variable.

## Documentation to maintain
- CHANGELOG.md: all changes under [Unreleased].
- decisions.md: append an entry for every choice you make that the
  task card did not specify. One entry, max ~6 lines, template
  below. Never delete or edit old entries.
- PROJECT.md: update the Status section at the end of each task.
- Versioning: SemVer 0.x. Tag at phase milestones only (v0.1, v0.2,
  ...) when the human requests it. Never change persisted save
  formats without a migration note in CHANGELOG.md.

## decisions.md entry template

## D-<NNN> — <short title> — <date>
Context: <1-2 lines>
Decision: <1-2 lines>
Alternatives: <1 line>
Decided-by: <planner | coding-agent>
Status: <Accepted in PR #<n>>

## Bootstrap note
main was created once by the human directly on GitHub (stub README)
before PR #1. There are NO exceptions to "never commit to or push
main", including empty, orphan, or bootstrap commits. If a base
branch is ever missing, stop and ask again.
