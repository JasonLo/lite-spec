# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repo.

## What this repo is

**lite-spec** — a toolkit of four `ls-` skills implementing a lightweight spec workflow:

```
ls-constitution → specs/CONSTITUTION.md   (non-negotiable principles)
ls-intent       → specs/INTENT.md         (problem, EARS outcomes, non-goals, constraints, change log)
ls-decisions    → specs/DECISIONS.md      (append-only one-line decisions, supersession-aware)
ls-check        → drift report            (code drift, intent drift, constitution drift)
```

The repo dogfoods its own toolkit — the artifacts in `specs/` are real outputs of the skills, not examples.

## Read before non-trivial work

Before generating output that touches design, architecture, scope, or skill behavior, load these. They override CLAUDE.md on conflict.

- **`specs/CONSTITUTION.md`** — non-negotiable principles. Every skill MUST validate against it; violations require an explicit `ls-constitution` amendment, never silent edits.
- **`specs/INTENT.md`** — current intent. The Outcome section uses EARS (`WHEN <trigger> THE SYSTEM SHALL <response>`) as testable success criteria.
- **`specs/DECISIONS.md`** — append-only architectural choices. Consult before re-litigating a settled question; supersede with a new entry rather than editing the old one.

## Skills

Skills live under `skills/ls-{check,constitution,decisions,intent}/SKILL.md`. Each is self-contained (YAML frontmatter: `name`, `description`, `allowed-tools`) and standalone — composition is encouraged, runtime coupling is forbidden (Constitution §4).
