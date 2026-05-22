# lite-spec

A toolkit of five Claude Code skills (the `ls-` family) for the AI-era spec workflow. Enough structure for a solo developer or small team to think clearly and capture decisions, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

Cycle: **bootstrap → principles → intent → decisions → drift check.**

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`ls-init`](skills/ls-init/SKILL.md) | `specs/` scaffold + `CLAUDE.md` pointers | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `specs/1_CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `specs/2_INTENT.md` | When describing a new feature. Produces a one-page doc with EARS-formatted acceptance criteria. |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `specs/3_DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale; supports supersession. |
| [`ls-check`](skills/ls-check/SKILL.md) | drift report (stdout) | When verifying code still satisfies intent. Reports code, intent, and constitution drift. |

Each skill is useful standalone; together they cover the full cycle.

## How it fits together

```
ls-init         ──► specs/ scaffold + CLAUDE.md pointer block (progressive disclosure)
ls-constitution ──► specs/1_CONSTITUTION.md ◄── validated against by every other skill
ls-intent       ──► specs/2_INTENT.md (EARS outcomes) ──Change Log append──► ls-check
ls-decisions    ──► specs/3_DECISIONS.md (append-only, supersession-aware)
ls-check         reads specs/2_INTENT.md + specs/1_CONSTITUTION.md + code, reports 3 drift types
```

Every artifact is plain Markdown stored in-repo. No external services, no databases, no CI hooks — invocation stays manual.

## Installation

One-liner — installs the `ls-` skills into `~/.claude/skills/`:

```bash
curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh
```

Per-project install (`./.claude/skills/`):

```bash
curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh -s -- --project
```

Re-running updates in place. Pin to a tag or commit SHA with `--ref` (recommended for production — `main` is mutable). To remove, swap `install.sh` for `uninstall.sh` in the URL.

Manual install (no curl):

```bash
cp -r skills/ls-* ~/.claude/skills/                   # global
cp -r skills/ls-* /path/to/project/.claude/skills/    # per-project
```

Invoke by name (e.g., `/ls-intent`) or by describing the task — keyword-rich descriptions in each skill's frontmatter trigger reliably.

## License

MIT (add a LICENSE file if you intend to publish).
