# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## What this repo is

**<project-name>** — short one-line description.

<!-- lite-spec:pointer-block:start -->

## Read before non-trivial work

Before generating output that touches design, architecture, scope, or behavior, load the spec files lazily — they override CLAUDE.md on conflict.

- **`specs/CONSTITUTION.md`** — non-negotiable principles. Every change to principles MUST go through `spec-constitution`; never edit silently.
- **`specs/INTENT/`** — one folder per intent (`I-N-<slug>/intent.md`); `experiments/`, `checks/`, and an optional `plan.md` sibling appear only on demand. Open intents have `status: draft` or `in_progress`; finished ones have `status: complete` or `superseded`. Outcomes use EARS (`WHEN <trigger> THE SYSTEM SHALL <response>`). Load only the intents whose scope intersects your task. Create/refine/supersede via `spec-intent`; `spec-check` derives `status` from outcome pass-counts.

When you're about to implement non-trivial behavior that no open intent covers, offer to capture it first via `/spec-intent propose` — it drafts an intent from context, the user accepts or refines, then you build. The offer is opt-in; if the user declines, proceed without it.

## Spec file ownership

Two tiers:

- **HUMAN-OWNED** — `specs/CONSTITUTION.md` (governance) and `specs/INTENT/` (product/scope — the whole tree, every `I-N-<slug>/intent.md`). AI agents MUST modify these only via `/spec-constitution` and `/spec-intent` respectively. Never with direct Edit/Write/sed, not even for a "trivial sync" like fixing a stale count. The exception is the skill-managed frontmatter fields on each `intent.md` (`status`, `closed`, `verdict_*`), which `spec-check` writes.
- **AGENT-WRITABLE** — `specs/INTENT/I-N-<slug>/plan.md` (per-intent implementation plan). It is drafted by `/spec-intent`'s planning handoff (which feeds the intent to `/plan`); it is a regenerable working doc — `intent.md` remains the source of truth.

Files outside `specs/` (README, this file, source, `SKILL.md` bodies, scripts) are fair game for normal edits.

## Spec workflow

This repo uses **lite-spec** — invoke the skills by name:

- `/spec-init` — bootstrap or repair the lite-spec setup
- `/spec-constitution` — ratify or amend principles (`specs/CONSTITUTION.md`)
- `/spec-intent` — open (`new` interview or fast `propose` draft), refine, or supersede an intent (`specs/INTENT/I-N-<slug>/intent.md`)
- `/spec-check` — drift report + status derivation across open intents

<!-- lite-spec:pointer-block:end -->
