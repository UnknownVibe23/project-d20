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
Status: Accepted in PR #1
