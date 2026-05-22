# lite-spec

A small set of Claude Code skills (the `ls-` family) for the AI-era spec workflow. Lite-spec gives a solo developer or small team enough structure to think clearly and capture decisions, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

The cycle is: **principles → intent → decisions → drift check.**

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `CONSTITUTION.md` | Once per project (and on amendments). Sets the non-negotiable principles every other skill validates against. |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `INTENT.md` | When describing a new feature in loose terms. Produces a one-page intent doc with EARS-formatted acceptance criteria. |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale; supports supersession. |
| [`ls-check`](skills/ls-check/SKILL.md) | report (stdout) | When you want to verify code still satisfies intent. Reports code drift, intent drift, and constitution drift. |

Each skill is useful standalone. Together, they cover the full lightweight spec cycle.

## How it fits together

```
ls-constitution ──┐
                  ├──► CONSTITUTION.md ◄── validated against by every other skill
ls-intent ────────┼──► INTENT.md (EARS outcomes)
                  │       │
                  │       └─── Change Log entry triggers ──► ls-check
ls-decisions ─────┴──► DECISIONS.md (append-only, supersession-aware)

ls-check reads INTENT.md + CONSTITUTION.md + code, reports 3 drift types.
```

Every artifact is plain Markdown stored in the repo alongside code. No external services, no databases, no CI hooks — invocation stays manual.

## Installation

Skills live under [`skills/`](skills/). To use them with Claude Code, copy the skill folders into your project's `.claude/skills/` directory (or your global `~/.claude/skills/` if you want them available everywhere):

```bash
cp -r skills/ls-* ~/.claude/skills/
```

Then invoke a skill by name in Claude Code (e.g., `/ls-intent`) or by describing what you want — the keyword-rich descriptions in each skill's frontmatter make them trigger reliably.

## The artifacts in this repo

This repo dogfoods its own toolkit:

- [`INTENT.md`](INTENT.md) — the intent for lite-spec itself
- [`CONSTITUTION.md`](CONSTITUTION.md) — the principles every `ls-` skill upholds
- [`DECISIONS.md`](DECISIONS.md) — bootstrap decisions for the toolkit
- [`CLAUDE.md`](CLAUDE.md) — thin pointers so Claude loads context lazily

## Constraints worth knowing

- Max 5 skills, all `ls-` prefixed
- Every `SKILL.md` body stays under 5,000 words
- Acceptance criteria are EARS (`WHEN <trigger> THE SYSTEM SHALL <response>`) so drift checks are mechanical
- Claude-first — no `AGENTS.md` portability layer
- Manual invocation — no git hooks, no CI integration

See [`CONSTITUTION.md`](CONSTITUTION.md) for the full list.

## License

MIT (add a LICENSE file if you intend to publish).
