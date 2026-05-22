---
name: ls-init
description: Initialize a repo to use the lite-spec workflow — create the specs/ scaffold, wire CLAUDE.md with progressive-disclosure pointers to CONSTITUTION/INTENT/DECISIONS, and stage next-step guidance. Use when bootstrapping a new project, adding lite-spec to an existing repo, or repairing a broken or partial setup. Triggers on "set up lite-spec", "initialize lite-spec", "bootstrap spec workflow", "add lite-spec to this repo", "wire up CLAUDE.md", "init specs", "/ls-init".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# ls-init

You are the bootstrap skill for **lite-spec**. You prepare a repo so the other `ls-` skills can run cleanly: you create the `specs/` directory, wire `CLAUDE.md` with thin pointers that load context lazily (progressive disclosure), and surface the next step the user should take.

This skill has two modes: **bootstrap** (no lite-spec markers present) and **repair** (some markers exist but the setup is incomplete or inconsistent). The skill MUST be idempotent — running it twice on the same repo MUST be safe and MUST NOT clobber existing content.

## Inputs

- The current working directory MUST be a git repository or an obvious project root (contains at least one of: `.git/`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or a top-level `README.md`). If none of these markers exist, refuse and ask the user to confirm they're in the right directory.
- No further user input is required. The user MAY pass a short project nickname/description; if given, use it in the CLAUDE.md preamble. If not, infer a name from the directory or the `README.md` first heading.

## Progressive Disclosure Rules You MUST Enforce

The whole point of this skill is to wire `CLAUDE.md` so Claude loads the *minimum* context up-front and pulls in the spec files only when relevant. To preserve that:

1. **NEVER inline the contents of `specs/1_CONSTITUTION.md`, `specs/2_INTENT.md`, or `specs/3_DECISIONS.md` into `CLAUDE.md`.** Pointer lines only.
2. **NEVER reproduce a skill's instructions inside `CLAUDE.md`.** Mention skills by name and folder; the `SKILL.md` files load themselves on invocation.
3. **Pointer lines for spec files MUST stay valid even if the target file doesn't exist yet.** `ls-constitution` / `ls-intent` / `ls-decisions` create the files on first use — the pointers should already be there waiting.
4. **`CLAUDE.md` body MUST stay under ~40 lines after this skill runs.** If it would exceed that, you're inlining too much — move content into `specs/` or a `docs/` file the pointer references.

## Mode Detection

Before doing anything, scan and classify:

- `specs/` exists? (directory)
- `specs/1_CONSTITUTION.md`, `specs/2_INTENT.md`, `specs/3_DECISIONS.md` — each present or absent?
- `CLAUDE.md` exists at the repo root?
- If `CLAUDE.md` exists, does it already contain a lite-spec pointer block (look for a heading like `## Read before non-trivial work` and the three `specs/*.md` paths)?
- Are the `ls-` skills installed somewhere reachable? Check `.claude/skills/ls-*` (per-project) and `~/.claude/skills/ls-*` (global). Report which (if any), but do NOT install them — that's the user's call.

**Bootstrap** = no `specs/` directory AND (no `CLAUDE.md` OR `CLAUDE.md` has no lite-spec pointer block).
**Repair** = anything else (partial setup detected).

## Mode 1 — Bootstrap

1. **Confirm the project root** using the markers listed in Inputs. If unsure, ask the user once.
2. **Create `specs/`** as an empty directory. Do NOT create `1_CONSTITUTION.md`, `2_INTENT.md`, or `3_DECISIONS.md` here — those go through their dedicated skills, which is the careful path. Add a `specs/.gitkeep` so the empty directory is checked in.
3. **Write or update `CLAUDE.md`** at the repo root with the pointer block below. If `CLAUDE.md` already exists, do NOT overwrite it — instead, append the pointer block as a new section after existing content, and leave the rest alone.
4. **Report** what was created, where the skills were found (or that they weren't), and the recommended next step (`/ls-constitution` if no constitution exists, otherwise `/ls-intent`).

### Required `CLAUDE.md` pointer block

The exact structure lives in [`CLAUDE.template.md`](CLAUDE.template.md) (sibling of this `SKILL.md`). Read that file at runtime, substitute `<project-name>` with the inferred or user-supplied name, and write the result to the target repo's `CLAUDE.md`. Keep all paths and headings verbatim so other skills can grep for them.

Notes on the block:
- The pointer lines reference files that may not yet exist. That's intentional — they become live once the corresponding skill runs for the first time.
- If `CLAUDE.md` already had a "What this repo is" section, do NOT overwrite it. Append only the "Read before non-trivial work", "Spec file ownership", and "Spec workflow" sections, and skip the `# CLAUDE.md` heading.
- The "Spec file ownership" section is load-bearing — it carries the two-tier taxonomy (HUMAN-OWNED vs. AGENT-WRITABLE) into every consumer repo, so future Claude sessions know which spec files they may touch directly. Keep its heading verbatim so other skills can detect its presence; never collapse it into a one-liner or drop one of the tiers.

## Mode 2 — Repair

The repair path MUST be conservative — never overwrite existing user content, never rewrite spec files, never renumber decisions. You're filling in gaps, not normalizing style.

1. **List what's present and what's missing** based on the mode-detection scan. Show the user the list before applying any change.
2. **Create `specs/`** if missing (with `.gitkeep`).
3. **Add the pointer block to `CLAUDE.md`** only if `CLAUDE.md` lacks it. If `CLAUDE.md` is absent entirely, create it with the full block. If it exists but lacks the block, append the "Read before non-trivial work", "Spec file ownership", and "Spec workflow" sections.
4. **Do NOT touch existing `specs/1_CONSTITUTION.md`, `specs/2_INTENT.md`, or `specs/3_DECISIONS.md`.** If one of these is missing, simply note it in the report and suggest the relevant skill.
5. **Validate against `specs/1_CONSTITUTION.md`** if it exists. The repair MUST NOT introduce CLAUDE.md content that violates a principle (e.g., inlining a large doc when the constitution caps doc lengths — the spirit applies to CLAUDE.md too).
6. **Report** the diff: what was added, what was left untouched, and which next skill the user should invoke for any missing spec file.

## Validation Rules You MUST Enforce

- **NEVER overwrite an existing `CLAUDE.md` body.** Append only.
- **NEVER create or modify `1_CONSTITUTION.md`, `2_INTENT.md`, or `3_DECISIONS.md` from within `ls-init`.** This skill is bootstrap-scope. The spec files are authored by their dedicated skills (`/ls-constitution`, `/ls-intent`, `/ls-decisions`); ls-init only creates the empty `specs/` scaffold. (This is about ls-init's role — not a universal rule about who may write to DECISIONS, which is agent-writable per the agent-writable taxonomy.)
- **NEVER omit the "Spec file ownership" section from the pointer block.** It carries the two-tier taxonomy into every consumer repo and is the only mechanism by which Claude learns which spec files are human-owned vs. agent-writable.
- **NEVER install the `ls-` skills** into `.claude/skills/` for the user. Report whether they're reachable; if not, point them at the README's installation snippet.
- **NEVER add `AGENTS.md` or other cross-tool portability files.**
- **NEVER add git hooks, CI integration, or external state files.**
- **NEVER inline spec contents into `CLAUDE.md`** (progressive disclosure).

## Output Contract

- `specs/` exists with a `.gitkeep` (only if it didn't already exist).
- `CLAUDE.md` exists at the repo root and contains the pointer block.
- A short stdout report:
  - Mode used (bootstrap or repair).
  - Files created vs. files left untouched.
  - Skill reachability (per-project vs. global vs. missing).
  - Recommended next step (specific skill to invoke).

## What This Skill MUST NOT Do

- NEVER write or modify any of the three spec files. ls-init is bootstrap-scope; authoring the spec files belongs to `/ls-constitution`, `/ls-intent`, and `/ls-decisions`. (This is an ls-init rule. At runtime, DECISIONS is agent-writable per the agent-writable taxonomy — but not via ls-init.)
- NEVER duplicate content into `CLAUDE.md` that already exists in a spec file or another doc.
- NEVER assume the user wants any particular initial principle, intent, or decision — surface the next step, then stop.
- NEVER fail silently. If the project root is ambiguous, ask the user once and stop until they answer.
