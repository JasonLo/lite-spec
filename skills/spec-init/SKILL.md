---
name: spec-init
description: Initialize a repo to use the lite-spec workflow — the specs/ tree and CLAUDE.md pointer block. Use when bootstrapping a new project, adding lite-spec to an existing repo, or repairing a broken or partial setup. Triggers on "set up lite-spec", "initialize lite-spec", "bootstrap spec workflow", "add lite-spec to this repo", "wire up CLAUDE.md", "init specs", "/spec-init".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# spec-init

You are the bootstrap skill for **lite-spec**. You prepare a repo so the other `spec-` skills can run cleanly: you create the `specs/` directory, wire `CLAUDE.md` with thin pointers that load context lazily (progressive disclosure), and surface the next step the user should take.

This skill has two modes: **bootstrap** (no lite-spec markers present) and **repair** (some markers exist but the setup is incomplete or inconsistent). The skill MUST be idempotent — running it twice on the same repo MUST be safe and MUST NOT clobber existing content.

## Inputs

- The current working directory MUST be a git repository or an obvious project root (contains at least one of: `.git/`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or a top-level `README.md`). If none of these markers exist, refuse and ask the user to confirm they're in the right directory.
- No further user input is required. The user MAY pass a short project nickname/description; if given, use it in the CLAUDE.md preamble. If not, infer a name from the directory or the `README.md` first heading.

## Progressive Disclosure Rules You MUST Enforce

The whole point of this skill is to wire `CLAUDE.md` so Claude loads the *minimum* context up-front and pulls in the spec files only when relevant. To preserve that:

1. **NEVER inline the contents of `specs/CONSTITUTION.md`, any `specs/INTENT/I-N-<slug>/intent.md`, or `specs/DECISIONS.md` into `CLAUDE.md`.** Pointer lines only.
2. **NEVER reproduce a skill's instructions inside `CLAUDE.md`.** Mention skills by name and folder; the `SKILL.md` files load themselves on invocation.
3. **Pointer lines for spec files MUST stay valid even if the target file doesn't exist yet.** `spec-constitution` / `spec-intent` / `spec-decisions` create the files on first use — the pointers should already be there waiting.
4. **`CLAUDE.md` body MUST stay under ~40 lines after this skill runs.** If it would exceed that, you're inlining too much — move content into `specs/` or a `docs/` file the pointer references.

## Mode Detection

Before doing anything, scan and classify:

- `specs/` exists? (directory)
- `specs/CONSTITUTION.md`, `specs/INTENT/` (directory), `specs/DECISIONS.md` — each present or absent?
- `CLAUDE.md` exists at the repo root?
- If `CLAUDE.md` exists, does it already contain a lite-spec pointer block (look for the marker `<!-- lite-spec:pointer-block:start -->`, the durable anchor this skill writes via its template — robust against cosmetic heading edits)?
- Are the `spec-` skills installed somewhere reachable? Check `.claude/skills/spec-*` (per-project) and `~/.claude/skills/spec-*` (global). Report which (if any), but do NOT install them — that's the user's call.

**Bootstrap** = no `specs/` directory AND (no `CLAUDE.md` OR `CLAUDE.md` has no lite-spec pointer block).
**Repair** = anything else (partial setup detected).

## Mode 1 — Bootstrap

1. **Confirm the project root** using the markers listed in Inputs. If unsure, ask the user once.
2. **Create `specs/` and `specs/INTENT/`** as empty directories. Do NOT create `CONSTITUTION.md`, any `I-N-<slug>/` folder, or `DECISIONS.md` here — those go through their dedicated skills, which is the careful path. Do NOT add `.gitkeep` files; each directory becomes meaningful (and committable) the first time a spec skill writes into it. `specs/INTENT/` is the only spec subdirectory `spec-init` creates — it pre-exists so `/spec-intent new` doesn't have to bootstrap the tree on first use.
3. **Write or update `CLAUDE.md`** at the repo root with the pointer block below. If `CLAUDE.md` already exists, do NOT overwrite it — instead, append the pointer block as a new section after existing content, and leave the rest alone.
4. **Report** what was created and where the skills were found (or that they weren't). End the report with `Next: /spec-constitution` — bootstrap creates an empty `specs/` tree, so `CONSTITUTION.md` is always missing after this run and ratifying it is the unambiguous next step. See "Handoff convention" below.

### Required `CLAUDE.md` pointer block

The exact structure lives in [`CLAUDE.template.md`](CLAUDE.template.md) (sibling of this `SKILL.md`). Read that file at runtime, substitute `<project-name>` with the inferred or user-supplied name, and write the result to the target repo's `CLAUDE.md`. Keep all paths and headings verbatim so other skills can grep for them.

Notes on the block:
- The pointer lines reference files that may not yet exist. That's intentional — they become live once the corresponding skill runs for the first time.
- The `<!-- lite-spec:pointer-block:start -->` and `<!-- lite-spec:pointer-block:end -->` HTML comments wrap the three lite-spec sections in the template. They are the durable anchor that other `spec-` skills grep for — keep them verbatim. Heading text inside the block is human-editable; the markers are not.
- If `CLAUDE.md` already exists, do NOT overwrite the file. Append only the three lite-spec sections ("Read before non-trivial work", "Spec file ownership", "Spec workflow"), wrapped in the start/end markers, after existing content. Always skip the `# CLAUDE.md` H1 and the "What this repo is" section when appending — those belong to the existing file. Emit the H1 and the "What this repo is" intro only when creating `CLAUDE.md` from scratch.
- The "Spec file ownership" section is load-bearing — it carries the two-tier taxonomy (HUMAN-OWNED vs. AGENT-WRITABLE) into every consumer repo, so future Claude sessions know which spec files they may touch directly. Never collapse it into a one-liner or drop one of the tiers.

## Mode 2 — Repair

The repair path MUST be conservative — never overwrite existing user content, never rewrite spec files, never renumber decisions. You're filling in gaps, not normalizing style.

1. **List what's present and what's missing** based on the mode-detection scan. Show the user the list before applying any change.
2. **Create `specs/` and `specs/INTENT/`** if missing. Do not add `.gitkeep` files — see the bootstrap note above.
3. **Add the pointer block to `CLAUDE.md`** only if `CLAUDE.md` lacks the `<!-- lite-spec:pointer-block:start -->` marker. If `CLAUDE.md` is absent entirely, create it with the full block (H1, "What this repo is", then the marker-wrapped three sections). If it exists but lacks the marker, append only the three lite-spec sections — wrapped in the start/end markers — after existing content. Never re-emit the `# CLAUDE.md` H1 or the "What this repo is" intro when appending to an existing file.
4. **Do NOT touch existing `specs/CONSTITUTION.md`, any `specs/INTENT/I-*-*/intent.md`, or `specs/DECISIONS.md`.** If one of these is missing, simply note it in the report and suggest the relevant skill (`/spec-constitution`, `/spec-intent new`, or `/spec-decisions`).
5. **Validate against `specs/CONSTITUTION.md`** if it exists. The repair MUST NOT introduce CLAUDE.md content that violates a principle (e.g., inlining a large doc when the constitution caps doc lengths — the spirit applies to CLAUDE.md too).
6. **Report** the diff: what was added, what was left untouched, and which next skill the user should invoke for any missing spec file. End the report with a single `Next:` line **only** when the next step is unambiguous: `Next: /spec-constitution` if `CONSTITUTION.md` is the sole missing spec file, else `Next: /spec-intent new` if the `INTENT/` tree is the sole gap. **Never emit `Next: /spec-decisions`** — `DECISIONS.md` is created lazily on first decision append (see `spec-decisions` Mode 1 step 2), so a missing log file is not a runnable next step; `/spec-decisions` requires the user to come with a decision to record. If multiple spec files are missing, or `DECISIONS.md` is the only gap, list the missing files as plain bullets and omit the `Next:` line — the user picks. See "Handoff convention" below.

## Handoff convention

Every skill in the lite-spec family ends its run report with at most one `Next: /<skill> [args]` line — the suggested next action when the post-state clearly implies one. **Omit the line entirely when the next action is code work, "nothing", or genuinely ambiguous** — silence is the terminal signal, and a stale or pushy "Next:" line is worse than none. The user is free to ignore the suggestion; it's a pointer, not a command.

## Validation Rules You MUST Enforce

- **NEVER overwrite an existing `CLAUDE.md` body.** Append only.
- **NEVER create or modify `CONSTITUTION.md`, any `INTENT/I-N-<slug>/intent.md`, or `DECISIONS.md` from within `spec-init`.** This skill is bootstrap-scope. The spec files are authored by their dedicated skills (`/spec-constitution`, `/spec-intent`, `/spec-decisions`); spec-init only creates the empty `specs/` and `specs/INTENT/` scaffold. (This is about spec-init's role — not a universal rule about who may write to DECISIONS, which is agent-writable per the agent-writable taxonomy.)
- **NEVER omit the "Spec file ownership" section from the pointer block.** It carries the two-tier taxonomy into every consumer repo and is the only mechanism by which Claude learns which spec files are human-owned vs. agent-writable.
- **NEVER install the `spec-` skills** into `.claude/skills/` for the user. Report whether they're reachable; if not, point them at the README's installation snippet.
- **NEVER add `AGENTS.md` or other cross-tool portability files.**
- **NEVER add git hooks, CI integration, or external state files.**
- **NEVER inline spec contents into `CLAUDE.md`** (progressive disclosure).

## Output Contract

- `specs/` and `specs/INTENT/` exist (both empty until a spec skill writes its first file — no `.gitkeep` in either).
- `CLAUDE.md` exists at the repo root and contains the marker-wrapped pointer block.
- A short stdout report:
  - Mode used (bootstrap or repair).
  - Files created vs. files left untouched.
  - Skill reachability (per-project vs. global vs. missing).
  - A conditional `Next: /<skill>` line per the Handoff convention above (omitted when the next action is ambiguous or there's nothing to suggest).

## What This Skill MUST NOT Do

- NEVER write or modify any of the three spec files. spec-init is bootstrap-scope; authoring the spec files belongs to `/spec-constitution`, `/spec-intent`, and `/spec-decisions`. (This is an spec-init rule. At runtime, DECISIONS is agent-writable per the agent-writable taxonomy — but not via spec-init.)
- NEVER duplicate content into `CLAUDE.md` that already exists in a spec file or another doc.
- NEVER assume the user wants any particular initial principle, intent, or decision — surface the next step, then stop.
- NEVER fail silently. If the project root is ambiguous, ask the user once and stop until they answer.
