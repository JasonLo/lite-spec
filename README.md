# lite-spec

A toolkit of four Claude Code skills (the `ls-` family) for the AI-era spec workflow. Enough structure for a solo developer or small team to think clearly and capture decisions, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

Cycle: **principles → intent → decisions → drift check.**

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `specs/CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `specs/INTENT.md` | When describing a new feature. Produces a one-page doc with EARS-formatted acceptance criteria. |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `specs/DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale; supports supersession. |
| [`ls-check`](skills/ls-check/SKILL.md) | drift report (stdout) | When verifying code still satisfies intent. Reports code, intent, and constitution drift. |

Each skill is useful standalone; together they cover the full cycle.

## How it fits together

```
ls-constitution ──► specs/CONSTITUTION.md ◄── validated against by every other skill
ls-intent       ──► specs/INTENT.md (EARS outcomes) ──Change Log append──► ls-check
ls-decisions    ──► specs/DECISIONS.md (append-only, supersession-aware)
ls-check         reads specs/INTENT.md + specs/CONSTITUTION.md + code, reports 3 drift types
```

Every artifact is plain Markdown stored in-repo. No external services, no databases, no CI hooks — invocation stays manual.

## Installation

```bash
cp -r skills/ls-* ~/.claude/skills/                   # global
cp -r skills/ls-* /path/to/project/.claude/skills/    # per-project
```

Invoke by name (e.g., `/ls-intent`) or by describing the task — keyword-rich descriptions in each skill's frontmatter trigger reliably.

## Dogfooded artifacts

This repo's [`specs/INTENT.md`](specs/INTENT.md), [`specs/CONSTITUTION.md`](specs/CONSTITUTION.md), and [`specs/DECISIONS.md`](specs/DECISIONS.md) are real outputs of the toolkit, not examples. [`CLAUDE.md`](CLAUDE.md) is a thin pointer file so Claude loads context lazily. See [`specs/CONSTITUTION.md`](specs/CONSTITUTION.md) for the full ruleset (max 5 skills, `ls-` prefix, EARS criteria, Claude-first, manual invocation, etc.).

## License

MIT (add a LICENSE file if you intend to publish).
