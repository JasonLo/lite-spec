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

1. `/ls-constitution             # once: ratify project principles (amend later as needed)`
1. `/ls-intent new "<title>"     # open a new intent: problem, EARS outcomes, non-goals`
1. `... write code ...`
1. `/ls-decisions                # log non-trivial choices (or let Claude append directly)`
1. `/ls-check                    # verify code still satisfies open intents + constitution`

Each `/ls-intent new` creates `specs/INTENT/IT-N-<slug>/intent.md` plus an `experiments/` subfolder. Multiple intents may be open at once; `/ls-check` iterates every non-terminal intent and derives each one's `status` from outcome pass-counts.

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`ls-init`](skills/ls-init/SKILL.md) | `specs/` + `specs/INTENT/` scaffold + `CLAUDE.md` pointers | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `specs/CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `specs/INTENT/IT-N-<slug>/intent.md` | When opening, refining, or superseding an intent. Each intent is its own folder with EARS outcomes and a nested `experiments/`. Frontmatter `status` is derived by `ls-check`. |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `specs/DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale and an `[intent: IT-N]` tag; supports supersession. Agent-writable. |
| [`ls-check`](skills/ls-check/SKILL.md) | drift report (stdout) + `intent.md` frontmatter writeback | Manual or auto-invoked — after edits to any `intent.md` or `CONSTITUTION.md`, as a pre-PR audit, or on phrases like "check for drift" / "verify against spec". Iterates every open intent; writes `status`, `verdict_*`, and `closed` back to each `intent.md`. |

## How it fits together

Plain Markdown, no external services. `CONSTITUTION.md` and the `INTENT/` tree are human-owned (skill-guided); `DECISIONS.md` is agent-writable. EARS outcomes (`WHEN <trigger> THE SYSTEM SHALL <response>`) let `ls-check` grade each SHALL against code and derive each intent's `status`. Decisions carry an `[intent: IT-N]` tag linking them back.
