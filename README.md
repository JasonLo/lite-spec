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

Each `/ls-intent new` creates `specs/INTENT/I-N-<slug>/intent.md` plus an `experiments/` subfolder. Multiple intents may be open at once; `/ls-check` iterates every non-terminal intent and derives each one's `status` from outcome pass-counts.

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`ls-init`](skills/ls-init/SKILL.md) | `specs/` + `specs/INTENT/` scaffold + `CLAUDE.md` pointers | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `specs/CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. In ratify mode, surveys the codebase first to propose candidate principles from observed conventions (test runner, linter, package manager, etc.). |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `specs/INTENT/I-N-<slug>/intent.md` | When opening, refining, or superseding an intent. Each intent is its own folder with EARS outcomes and a nested `experiments/`. Frontmatter `status` is derived by `ls-check`. |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `specs/DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale and an `[intent: I-N]` tag; supports supersession. Agent-writable. |
| [`ls-check`](skills/ls-check/SKILL.md) | drift report (stdout) + `intent.md` frontmatter writeback | Manual or auto-invoked — after edits to any `intent.md` or `CONSTITUTION.md`, as a pre-PR audit, or on phrases like "check for drift" / "verify against spec". Iterates every open intent; writes `status`, `verdict_*`, and `closed` back to each `intent.md`. |

## How it fits together

Plain Markdown, no external services. `CONSTITUTION.md` and the `INTENT/` tree are human-owned (skill-guided); `DECISIONS.md` is agent-writable. EARS outcomes (`WHEN <trigger> THE SYSTEM SHALL <response>`) let `ls-check` grade each SHALL against code and derive each intent's `status`. Decisions carry an `[intent: I-N]` tag linking them back.

## Test-backed verdicts

Each EARS outcome may carry a `[test: <runner>:<target>]` citation. When present, `ls-check` runs the citation and uses the result — not an LLM grep — to decide pass vs. fail. Two flavors of runner exist:

**Process runners** (`pytest`, `vitest`, `jest`, `cargo`, `go`, `npm`, `shell`) — invoked via Bash; exit code 0 is the only path to a test-backed pass.

```markdown
- **WHEN** user submits the form **THE SYSTEM SHALL** show a toast within 200ms. [test: pytest:tests/test_form.py::test_toast_latency]
```

**Agent runner** (`agent:<path-to-prompt-file>`) — for SHALLs that can't be expressed as a deterministic test (UX copy tone, doc structure, narrative consistency). `ls-check` spawns a subagent against the prompt file plus the EARS line, the subagent emits a structured `pass`/`fail`/`unverifiable` verdict with file:line evidence, and the verdict + reason + citations are surfaced in the drift report.

```markdown
- **WHEN** an error blocks the user **THE SYSTEM SHALL** show concise, actionable copy. [test: agent:specs/INTENT/I-3-onboarding/checks/error_copy_tone.md]
```

The prompt file (`specs/INTENT/I-3-onboarding/checks/error_copy_tone.md`) is seeded with the SHALL by `/ls-intent` on first cite; the user enriches its `## Success criteria` section with concrete pass conditions.

`ls-check` writes three ratios back to the intent's frontmatter, forming a strength ladder:

- `verdict_outcomes_passed/_total` — overall passes.
- `verdict_outcomes_passed_by_agent/_total` — passes verified by at least a subagent check or a process-runner test.
- `verdict_outcomes_passed_by_test/_total` — passes verified by a process-runner test (strictest signal).

Invariant: `_passed_by_test ≤ _passed_by_agent ≤ _passed ≤ _total`. Outcomes without any `[test: ...]` citation are classified `unverifiable` — there is no grep + LLM fallback. The goal is to drive `_passed_by_test/_total` toward 1.0 over time, falling back to the `agent:` runner only when a SHALL is genuinely unprogrammable.
