# lite-spec

A toolkit of five Claude Code skills (the `ls-` family) for the AI-era spec workflow. Enough structure for a solo developer or small team to think clearly and capture decisions, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

Cycle: **bootstrap → principles → intent → decisions → drift check.**

## The skills

| Skill | Artifact | Audience | When to use |
|---|---|---|---|
| [`ls-init`](skills/ls-init/SKILL.md) | `specs/` scaffold + `CLAUDE.md` pointers | Human | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`ls-constitution`](skills/ls-constitution/SKILL.md) | `specs/1_CONSTITUTION.md` | Human | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. |
| [`ls-intent`](skills/ls-intent/SKILL.md) | `specs/2_INTENT.md` | Human | When describing a new feature. Produces a one-page doc with EARS-formatted outcomes (acceptance criteria the drift checker can grade mechanically). |
| [`ls-decisions`](skills/ls-decisions/SKILL.md) | `specs/3_DECISIONS.md` | Both | When you make a non-trivial choice. Appends a one-line entry with rationale; supports supersession. Agent-writable: Claude may append directly, or humans can use the guided path. |
| [`ls-check`](skills/ls-check/SKILL.md) | drift report (stdout) | Both | When verifying code still satisfies intent. Agent runs the SHALL-by-SHALL check; human reviews the report (code, intent, and constitution drift). |

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

The `CLAUDE.md` pointer block that `ls-init` writes also carries a two-tier ownership taxonomy into the consuming repo: `1_CONSTITUTION.md` and `2_INTENT.md` are **human-owned** (only modifiable via `/ls-constitution` and `/ls-intent`), while `3_DECISIONS.md` is **agent-writable** (Claude may append directly, subject to constitution validation and the entry format). This keeps governance and product scope behind the guided path while letting AI capture engineering choices at coding speed.

## Quickstart

**1. Install the skills.**

```bash
curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh
```

The installer prompts where to install: **project** (`./.claude/skills/`, default) or **global** (`~/.claude/skills/`). Skip the prompt with `--project` or `--global`. Pin a ref with `--ref TAG_OR_SHA` (recommended for production — `main` is mutable). To uninstall, swap `install.sh` for `uninstall.sh` in the URL. Manual install: `cp -r skills/ls-* ./.claude/skills/` (or `~/.claude/skills/`).

**2. Bootstrap the repo.** In a Claude Code session inside your project:

```
/ls-init
```

Creates `specs/` and wires the `CLAUDE.md` pointer block so future Claude sessions know which spec files are human-owned vs. agent-writable.

**3. Basic flow.**

```
/ls-constitution    # once: ratify project principles (amend later as needed)
/ls-intent          # capture each new feature: problem, EARS outcomes, non-goals
... write code ...
/ls-check           # verify code still satisfies intent + constitution
/ls-decisions       # log non-trivial choices (or let Claude append directly)
```

Invoke by name as above, or by describing the task — keyword-rich descriptions in each skill's frontmatter trigger reliably.

## License

MIT (add a LICENSE file if you intend to publish).
