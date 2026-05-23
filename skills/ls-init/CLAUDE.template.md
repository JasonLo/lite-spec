# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## What this repo is

**<project-name>** — short one-line description.

<!-- lite-spec:pointer-block:start -->

## Read before non-trivial work

Before generating output that touches design, architecture, scope, or behavior, load the spec files lazily — they override CLAUDE.md on conflict.

- **`specs/CONSTITUTION.md`** — non-negotiable principles. Every change to principles MUST go through `ls-constitution`; never edit silently.
- **`specs/INTENT/`** — one folder per intent (`I-N-<slug>/intent.md`), with experiments nested inside. Open intents have `status: draft` or `in_progress`; finished ones have `status: complete` or `superseded`. Outcomes use EARS (`WHEN <trigger> THE SYSTEM SHALL <response>`). Load only the intents whose scope intersects your task. Create/refine/supersede via `ls-intent`; `ls-check` derives `status` from outcome pass-counts.
- **`specs/DECISIONS.md`** — append-only architectural choices. New entries carry an `[intent: I-N]` tag. Consult before re-litigating a settled question; supersede via `ls-decisions` rather than editing.

## Spec file ownership

Two tiers:

- **HUMAN-OWNED** — `specs/CONSTITUTION.md` (governance) and `specs/INTENT/` (product/scope — the whole tree, every `I-N-<slug>/intent.md`). AI agents MUST modify these only via `/ls-constitution` and `/ls-intent` respectively. Never with direct Edit/Write/sed, not even for a "trivial sync" like fixing a stale count. The exception is the skill-managed frontmatter fields on each `intent.md` (`status`, `closed`, `verdict_*`), which `ls-check` writes.
- **AGENT-WRITABLE** — `specs/DECISIONS.md` (engineering log). AI agents MAY append or supersede entries directly, OR via `/ls-decisions` for the guided path. Direct writes MUST follow the format in `ls-decisions`, validate against the constitution first, carry an `[intent: I-N]` tag, and only record decisions settled with the human in the current conversation (no phantom commitments).

Files outside `specs/` (README, this file, source, `SKILL.md` bodies, scripts) are fair game for normal edits.

## Spec workflow

This repo uses **lite-spec** — invoke the skills by name:

- `/ls-init` — bootstrap or repair the lite-spec setup
- `/ls-constitution` — ratify or amend principles (`specs/CONSTITUTION.md`)
- `/ls-intent` — draft, refine, or supersede an intent (`specs/INTENT/I-N-<slug>/intent.md`)
- `/ls-decisions` — log a decision (`specs/DECISIONS.md`)
- `/ls-check` — drift report + status derivation across open intents

<!-- lite-spec:pointer-block:end -->
