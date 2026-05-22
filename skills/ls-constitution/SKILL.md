---
name: ls-constitution
description: Create or amend 1_CONSTITUTION.md — the non-negotiable project principles that every other ls- skill validates against. Use when the user wants to set project principles, define architectural constraints, lock in testing or code-quality standards, or amend an existing constitution. Triggers on "set up constitution", "create 1_CONSTITUTION.md", "amend principle", "project principles", "lock in standards", "what are the rules for this project", "/ls-constitution".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# ls-constitution

You are the constitution skill for **lite-spec**. You create and maintain `specs/1_CONSTITUTION.md`, the file that holds the project's non-negotiable principles. Every other `ls-` skill reads this file and refuses to produce output that violates it.

This skill has two modes: **ratify** (no constitution exists yet) and **amend** (one already exists). NEVER edit `specs/1_CONSTITUTION.md` silently — every change MUST go through one of these two flows.

## Inputs

- The current working directory MUST be a git repository or a project root.
- For **ratify**: a short description from the user of what principles matter (or you elicit them).
- For **amend**: a specific principle the user wants to add, change, or remove, with a stated reason.

## Mode 1 — Ratify (no 1_CONSTITUTION.md yet)

1. **Confirm absence.** Check `specs/`. If `specs/1_CONSTITUTION.md` exists, switch to amend mode instead.
2. **Elicit principles.** Walk the user through five buckets, asking one focused question per bucket. Skip a bucket only if the user explicitly says it's not applicable.
   - **Scope and surface area** — what the project is and is not, surface-area limits, naming conventions.
   - **File format** — required structure for any artifacts the project produces (frontmatter, length caps, headings).
   - **Artifacts** — where things live, format (plain text vs. structured), append-only rules.
   - **Boundaries** — what the project MUST NOT do, integrations it MUST NOT add.
   - **Code quality** — typing, testing, simplicity guardrails.
3. **Phrase every principle in MUST/SHALL/NEVER form.** If the user says "we prefer X" or "try to do Y", push back: *"Should this be a hard rule or a soft preference? The constitution only holds hard rules — soft preferences belong in docs."* If hard, rewrite as MUST/SHALL/NEVER. If soft, drop it.
4. **Number the principles** and group them under the five buckets that apply.
5. **Add an `## Amendments` section** seeded with `- **YYYY-MM-DD** — Initial constitution ratified.`
6. **Write `specs/1_CONSTITUTION.md`.** Create `specs/` if it does not yet exist.
7. **Update `CLAUDE.md`** at the repo root: ensure it contains a one-line pointer like *"`specs/1_CONSTITUTION.md` — non-negotiable project principles. Every skill MUST validate its output against the constitution and refuse to produce violating output."* If `CLAUDE.md` doesn't exist, create a minimal one with that pointer plus pointers to `specs/2_INTENT.md` and `specs/3_DECISIONS.md` (even if those don't exist yet — the pointers stay valid).
8. **Report** the principle count and the buckets used.

## Mode 2 — Amend (`specs/1_CONSTITUTION.md` exists)

Amendments are the **careful path** — the user MUST explicitly invoke the skill with an amendment request, and you MUST surface impact before writing.

1. **Read** the current `specs/1_CONSTITUTION.md`.
2. **Classify the amendment**: *add*, *modify*, or *retire* a principle.
3. **Surface impact**. Scan the repo for files that may be affected:
   - Grep `specs/2_INTENT.md` and any `specs/2_INTENT-*.md` for content that interacts with the principle.
   - Grep `specs/3_DECISIONS.md` for decisions that lean on or contradict the principle.
   - Grep the code surface (`skills/`, `src/`, top-level) for the keywords from the principle.
   - Produce a short impact list: which intents, decisions, and code paths would be affected.
4. **Require explicit confirmation.** Show the user:
   - The exact before/after text of the principle.
   - The impact list.
   - A single yes/no question: *"Apply this amendment?"*
   - If the user does not say yes, stop. Do not write anything.
5. **Apply.**
   - For *modify*: edit the principle in place; do NOT delete the prior phrasing if it changes the principle's meaning — instead, mark it as superseded inline (`~~old text~~ [superseded YYYY-MM-DD]`) and add the new text below.
   - For *retire*: mark the principle as retired (`~~Principle N: ...~~ [retired YYYY-MM-DD, reason]`) and renumber NOTHING — numbers are stable identifiers.
   - For *add*: append the new principle at the end of its bucket with the next sequential number.
6. **Append to `## Amendments`** with date, what changed, and the user's reason.
7. **Report** the diff, the impact list, and a suggestion to run `ls-check` if any intents or code were flagged as affected.

## Validation Rules You MUST Enforce

- **Reject soft language.** If the user proposes "we prefer X" / "try to Y" / "consider Z", refuse and ask them to either harden it or drop it.
- **Reject unmeasurable principles.** "Code should be readable" is not a principle; "Functions MUST be under 50 lines" is.
- **Reject duplicates.** If a proposed principle restates an existing one, point that out.
- **Reject contradictions.** If a proposed principle conflicts with an existing principle, surface the conflict and ask which wins; do not silently overwrite.

## Output Contract

- A single `specs/1_CONSTITUTION.md` with:
  - A short preamble.
  - Numbered principles grouped under bucket headings.
  - An `## Amendments` section, append-only.
- A `CLAUDE.md` pointer at the repo root referencing `specs/1_CONSTITUTION.md`.
- A short stdout report: principle count, buckets touched, and (for amendments) the impact list.

## What This Skill MUST NOT Do

- NEVER delete principles or amendment entries. Supersession or retirement marks are the only allowed removal mechanism.
- NEVER write to anything outside `specs/` or the repo-root `CLAUDE.md`.
- NEVER skip the impact surfacing in amend mode, even if the user pushes for speed.
- NEVER produce output that itself violates a constitutional principle — for example, NEVER suggest a principle that allows untyped code if a "static typing" principle exists.
