# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## What this repo is

**<project-name>** — short one-line description.

## Read before non-trivial work

Before generating output that touches design, architecture, scope, or behavior, load the spec files lazily — they override CLAUDE.md on conflict.

- **`specs/1_CONSTITUTION.md`** — non-negotiable principles. Every change to principles MUST go through `ls-constitution`; never edit silently.
- **`specs/2_INTENT.md`** — current intent. Outcomes use EARS (`WHEN <trigger> THE SYSTEM SHALL <response>`) as testable success criteria. Refine via `ls-intent`.
- **`specs/3_DECISIONS.md`** — append-only architectural choices. Consult before re-litigating a settled question; supersede via `ls-decisions` rather than editing.

## Spec file ownership

Two tiers:

- **HUMAN-OWNED** — `specs/1_CONSTITUTION.md` (governance) and `specs/2_INTENT.md` (product/scope). AI agents MUST modify these only via `/ls-constitution` and `/ls-intent` respectively. Never with direct Edit/Write/sed, not even for a "trivial sync" like fixing a stale count.
- **AGENT-WRITABLE** — `specs/3_DECISIONS.md` (engineering log). AI agents MAY append or supersede entries directly, OR via `/ls-decisions` for the guided path. Direct writes MUST follow the format in `ls-decisions`, validate against the constitution first, and only record decisions settled with the human in the current conversation (no phantom commitments).

Files outside `specs/` (README, this file, source, `SKILL.md` bodies, scripts) are fair game for normal edits.

## Spec workflow

This repo uses **lite-spec** — invoke the skills by name:

- `/ls-init` — bootstrap or repair the lite-spec setup
- `/ls-constitution` — ratify or amend principles (`specs/1_CONSTITUTION.md`)
- `/ls-intent` — draft or refine intent (`specs/2_INTENT.md`)
- `/ls-decisions` — log a decision (`specs/3_DECISIONS.md`)
- `/ls-check` — drift report against intent + constitution
