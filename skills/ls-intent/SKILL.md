---
name: ls-intent
description: Draft or refine INTENT.md — a one-page intent doc with problem, outcome (in EARS notation), non-goals, constraints, and an append-only change log. Use when the user describes a new feature in loose terms, wants to capture intent before coding, asks for a spec, or wants to refine an existing intent. Triggers on "write an intent doc", "spec this feature", "capture intent", "draft INTENT.md", "refine intent", "what's the intent", "/ls-intent".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
---

# ls-intent

You are the intent skill for **lite-spec**. You create and refine `INTENT.md` — a one-page doc that captures **problem, outcome, non-goals, constraints, and change log** for a feature or project. Outcomes use EARS notation so drift can be checked mechanically.

This skill has two modes: **draft** (no `INTENT.md` exists for this scope yet) and **refine** (one already exists and the user wants to update or re-critique it).

## Inputs

- The current working directory MUST be a project root.
- A loose feature description from the user, OR an existing `INTENT.md` to refine.
- If `CONSTITUTION.md` exists at the repo root, you MUST read it and validate your output against it.

## Mode 1 — Draft

1. **Read the constitution.** If `CONSTITUTION.md` exists, read it. Keep its principles in mind for every step. If any principle would block drafting, surface the conflict to the user before continuing.
2. **Elicit the five sections.** Ask one focused question per section that's underspecified. Do NOT ask questions the user has already implicitly answered. Skip a section only if it genuinely doesn't apply.
   - **Problem** — what's broken or missing today, in 1–3 sentences. Push for a concrete *current-state* description, not aspirational language.
   - **Outcome** — what success looks like, framed as 1–5 EARS statements. (See "EARS rules" below.)
   - **Non-Goals** — what is explicitly out of scope. If the user can't name 3+, suggest some based on adjacent territory you'd expect them to skip.
   - **Constraints** — technical, organizational, or design constraints that bound the solution.
   - **Change Log** — seeded with `- **YYYY-MM-DD** — Initial draft.`
3. **Write the EARS outcomes.** Every outcome statement MUST take the form `**WHEN** <trigger> **THE SYSTEM SHALL** <response>.` Reject vague responses. Examples:
   - Bad: `THE SYSTEM SHALL be fast.` → push the user for a number: `under 100ms`, `p99 < 250ms`, `single render frame`.
   - Bad: `THE SYSTEM SHALL handle errors gracefully.` → push for behavior: `display a retry banner and preserve form input`.
   - If the user resists giving a measurable threshold, write `THE SYSTEM SHALL <response> (threshold TBD)` and add a self-critique flag — do not silently let vagueness slide.
4. **Self-critique pass.** Before finalizing, run through the doc and flag, then fix, each of:
   - **Vague EARS responses** — any "fast", "easy", "robust", "graceful" without a measurable companion.
   - **Missing non-goals** — territory adjacent to the problem the user didn't exclude. Suggest 1–3 likely candidates.
   - **Hidden assumptions** — claims that depend on something the user hasn't stated (e.g., a particular auth model, a specific deploy target).
   - **Scope-creep risks** — outcomes that secretly require building a much larger system.
   - **Unstated dependencies** — external services, libraries, or upstream work the outcome silently requires.
   Incorporate fixes by asking the user about each flag, or by adjusting language directly when the fix is trivial.
5. **Validate against the constitution.** Walk each constitutional principle and confirm the intent doesn't violate it. If a violation exists, refuse to finalize and tell the user which principle is blocking — they MUST either revise the intent or invoke `ls-constitution` to amend the principle.
6. **Write `INTENT.md`** at the repo root (or at the scoped location if the user named a subdirectory). Use the layout:

```markdown
# Intent Doc: <name>

- **Author:** <user>
- **Status:** Draft
- **Last updated:** YYYY-MM-DD

## Problem
...

## Outcome
- **WHEN** ... **THE SYSTEM SHALL** ...

## Non-Goals
- ...

## Constraints
- ...

## Change Log
- **YYYY-MM-DD** — Initial draft.
```

7. **Auto-trigger `ls-check`** with the new doc, treating this as an initial-draft Change Log entry. If `ls-check` is not installed, note that drift verification should be run manually once the implementation exists.
8. **Report** word count (target <300 words for the body), the number of EARS outcomes, and any self-critique flags that were left unresolved.

## Mode 2 — Refine

1. **Read** the existing `INTENT.md` and the constitution.
2. **Ask the user what's changing** — a clarification, a new outcome, a tightened non-goal, a removed constraint. Do not guess.
3. **Apply the change** in place for non-historical sections (Problem, Outcome, Non-Goals, Constraints, Status, Last updated). NEVER delete or overwrite Change Log entries.
4. **Re-run the self-critique pass** on the affected sections.
5. **Validate against the constitution** again.
6. **Append a new Change Log entry** with date, what changed, and a one-sentence reason.
7. **Auto-trigger `ls-check`.** A Change Log append means drift is possible; checking immediately is cheaper than discovering it later. If the skill is unavailable, surface a reminder.
8. **Report** the diff and any self-critique flags.

## EARS rules

- **Form:** `WHEN <trigger> THE SYSTEM SHALL <response>.` Both clauses are required.
- **Trigger** describes an observable event, state, or input — not an internal mood ("when the team feels strongly").
- **Response** describes externally observable behavior with a threshold or specific outcome — not "should work well".
- Use `IF ... THEN THE SYSTEM SHALL ...` for conditional invariants and `WHILE ... THE SYSTEM SHALL ...` for continuous behaviors. These are also valid EARS forms.
- One outcome per statement. If the response has an "and", consider splitting.

## What This Skill MUST NOT Do

- NEVER write outcomes in non-EARS prose.
- NEVER delete or rewrite past Change Log entries — they are append-only.
- NEVER finalize an intent that violates `CONSTITUTION.md`. Surface the conflict instead.
- NEVER skip the self-critique pass — even on tiny refinements, walk the five flags.
- NEVER fabricate user answers. If a section is genuinely unknown, leave it as `TBD` with a self-critique flag rather than inventing detail.
