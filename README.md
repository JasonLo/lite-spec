# lite-spec

> **Status:** experimental — interfaces may change before v1.

A toolkit of five Claude Code skills (the `ls-` family) for the AI-era spec workflow. Enough structure for a solo developer or small team to think clearly and capture decisions, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

## Quickstart

Requires [Claude Code](https://claude.com/claude-code). Skills are modular agent capabilities Claude Code loads from `./.claude/skills/` (per-project) or `~/.claude/skills/` (global).

### Install the skills

```bash
curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh
```

### Bootstrap the repo

```claude
/ls-init
```

Creates `specs/` and wires the `CLAUDE.md` pointer block so future Claude sessions know which spec files are human-owned vs. agent-writable.

### Basic flow

1. `/ls-constitution    # once: ratify project principles (amend later as needed)`
1. `/ls-intent          # capture each new feature: problem, EARS outcomes, non-goals`
1. `... write code ...`
1. `/ls-decisions       # log non-trivial choices (or let Claude append directly)`
1. `/ls-check           # verify code still satisfies intent + constitution (or let Claude auto-invoke)`

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`ls-init`](skills/ls-init/SKILL.md) | `specs/` scaffold + `CLAUDE.md` pointers | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `specs/1_CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `specs/2_INTENT.md` | When describing a new feature. Produces a one-page doc with EARS outcomes (acceptance criteria the drift checker can grade mechanically). |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `specs/3_DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale; supports supersession. Agent-writable: Claude may append directly, or humans can use the guided path. |
| [`ls-check`](skills/ls-check/SKILL.md) | drift report (stdout) | Manual or auto-invoked — after edits to `2_INTENT.md` or `1_CONSTITUTION.md`, as a pre-PR audit, or on phrases like "check for drift" / "verify against spec". Agent runs the SHALL-by-SHALL pass; human reviews the report (code, intent, and constitution drift). |

## How it fits together

Every artifact is plain Markdown in-repo — no external services, databases, or CI hooks. `1_CONSTITUTION.md` and `2_INTENT.md` are human-owned (guided path only); `3_DECISIONS.md` is agent-writable so Claude can append at coding speed. Intent outcomes use **EARS** (Easy Approach to Requirements Syntax) — phrased as `WHEN <trigger> THE SYSTEM SHALL <response>` (with `WHILE …` for continuous behavior and `IF … THEN THE SYSTEM SHALL …` for conditional invariants) — so `ls-check` can match each SHALL to code mechanically.

## What the outputs look like

A line appended to `specs/3_DECISIONS.md`:

```
D-0007: Decided to adopt SQLite over Postgres for local dev because zero-setup matters more than concurrency at this stage (2026-05-22). Supersedes D-0003.
```

A drift report printed by `/ls-check`:

```markdown
# ls-check report — 2026-05-22

## Code drift
- [x] O-1: WHEN the user clicks Save, THE SYSTEM SHALL persist edits — pass. Implemented at src/profile.tsx:42.
- [ ] O-2: WHILE editing, THE SYSTEM SHALL auto-save within 500ms — fail. No debounce found in src/profile.tsx.
- [?] O-3: WHEN navigating between pages, THE SYSTEM SHALL feel responsive — unverifiable. Re-invoke /ls-intent to refine.

## Constitution drift
- [ ] Principle 3 (no third-party CDNs) — fail. src/layout.tsx imports @vercel/analytics.

## Summary
1 pass, 2 fail, 1 unverifiable, 0 intent-ahead.
```
