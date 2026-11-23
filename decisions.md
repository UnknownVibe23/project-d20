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
