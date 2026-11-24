# Project D20 — Project Context

Goal: personal AI Game Master for solo play of D&D-style modules and
custom sandboxes. LLM (Mistral API) narrates; Python + SQLite own all
rules and state. Self-built web-grid VTT later. Rules authority:
SRD 5.2 (CC-BY-4.0), attribution in README.

Phases: 0 skeleton + dice -> 1 narrator loop -> 2 database + rules
engine -> 3 module runner -> 4 VTT -> 5 campaign polish.

## Status
- Current phase: 1 (narrator loop) — in progress
- Last completed task: Task 3-narrator-loop (narrator loop + play journal + `d20.play` CLI, PR #5)
- Task P1-F1: narrator client timeout (MISTRAL_TIMEOUT, default 120s) + structured-content reply extraction in review (PR #6)
- Next: Phase 2 (database + rules engine)
