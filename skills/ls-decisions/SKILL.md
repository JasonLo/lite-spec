---
name: ls-decisions
description: Append a one-line decision entry to 3_DECISIONS.md, or supersede an existing one. Use when the user has made a non-trivial choice during development (architecture, library, approach, scope cut) and wants it captured durably. Triggers on "log a decision", "record this choice", "add to 3_DECISIONS.md", "we decided X", "supersede decision", "/ls-decisions".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# ls-decisions

You are the decisions skill for **lite-spec**. You maintain `specs/3_DECISIONS.md` — an append-only log of non-trivial decisions with rationale. Each entry is a single line: `D-NNNN: Decided X because Y (YYYY-MM-DD).`

This skill has two modes: **append** (a new decision) and **supersede** (a past decision is being reversed).

## Inputs

- The current working directory MUST be a project root.
- A description of the decision from the user (the "X") and a reason (the "Y").
- If `specs/1_CONSTITUTION.md` exists, you MUST read it and validate the decision against it.

## Mode 1 — Append

1. **Read the constitution.** If `specs/1_CONSTITUTION.md` exists, read it. Cross-check the proposed decision against every principle.
2. **Read `specs/3_DECISIONS.md`.** If it doesn't exist, create it (creating `specs/` first if needed) with this header:

```markdown
# Decisions Log

Append-only log of non-trivial decisions. Each entry: `D-NNNN: Decided X because Y (YYYY-MM-DD).`
```

3. **Pick the next ID.** Scan existing `D-NNNN` IDs and use the next sequential number, four digits zero-padded.
4. **Deduplicate.** Grep `specs/3_DECISIONS.md` for keywords from the proposed decision. If a near-duplicate exists, surface it and ask the user whether to (a) skip — the choice is already recorded, (b) supersede the prior entry (switch to supersede mode), or (c) append anyway because the new entry is meaningfully different. Do not silently double-log.
5. **Validate against the constitution.** If the decision would violate a principle, refuse and tell the user which principle is blocking. They MUST either revise the decision or invoke `ls-constitution` to amend the principle.
6. **Check durability.** The entry MUST still make sense 6 months later. If the "because Y" reduces to "because we wanted to" or "because it's better", push back and ask for a concrete tradeoff (what was the alternative, what made this one win). If the user genuinely can't articulate a tradeoff, the decision probably isn't durable enough to log — say so.
7. **Aim for under 25 words.** A decision entry is one sentence, not a paragraph. If the rationale needs more, link to an INTENT or a doc rather than expanding inline.
8. **Append** the entry to `specs/3_DECISIONS.md`.
9. **Check the `CLAUDE.md` pointer block.** Look for the anchor heading `## Read before non-trivial work` in `CLAUDE.md` at the repo root — this is the unique heading `ls-init` writes via its template. If the anchor is present, the pointer block is already wired; do nothing. If the anchor is missing (or `CLAUDE.md` itself is missing), tell the user to run `/ls-init` to wire `CLAUDE.md`. Do NOT write any pointer text from this skill — `ls-init` is the single source of truth for `CLAUDE.md`.
10. **Report** the new ID, the entry text, and a confirmation that the constitution check passed.

## Mode 2 — Supersede

1. **Identify the prior entry.** The user MUST name the ID being superseded (e.g., `D-0042`). If they don't, ask. Then read that line.
2. **Pick the next ID** for the new entry.
3. **Run the same checks** as append mode (constitution, deduplication against *other* entries, durability).
4. **Strike the prior entry inline** with markdown strikethrough plus an annotation:
   ```
   - ~~**D-0042:** Decided REST because X (2026-01-10).~~ [superseded by D-0073, 2026-05-22]
   ```
   NEVER delete the original text. Strikethrough preserves history while making current state unambiguous.
5. **Append the new entry** with an explicit supersession marker:
   ```
   - **D-0073:** Supersedes D-0042 — switched to GraphQL because <reason> (2026-05-22).
   ```
6. **Report** both entries and the constitution-check result.

## Direct writes (without invoking this skill)

This skill is the **guided path** — it elicits, deduplicates, checks durability, and reports a constitution-validation result. But `specs/3_DECISIONS.md` is agent-writable by design — AI agents MAY also write to it directly when speed matters, subject to these rules:

1. **Read the constitution first.** If `specs/1_CONSTITUTION.md` exists, cross-check the proposed entry against every principle. If it violates a principle, do not write — surface the conflict and stop. (Same blocking rule as Mode 1 step 5.)
2. **Follow the format spec exactly.** `D-NNNN: Decided X because Y (YYYY-MM-DD).` — four-digit sequential ID (scan existing entries for the next number), entry under 25 words, rationale must reference a tradeoff/constraint/external requirement (no bare "because we decided" or "because it's better").
3. **Never log phantom commitments.** Only record decisions settled *with the human in the current conversation* — made by the human, or proposed by AI and explicitly accepted by the human. Autonomous AI choices made without explicit human assent belong in chat or a PR description, not in `3_DECISIONS.md`.
4. **Supersession via direct write is allowed.** Follow Mode 2 steps 4–5: strike the prior entry with `[superseded by D-NNNN, YYYY-MM-DD]`, then append the new entry with `Supersedes D-NNNN — ...`. Never delete a prior line.
5. **Append-only history still applies.** Editing the content of an existing decision line is forbidden; the only mutation is the supersession annotation.

When in doubt — durability is unclear, the human's position is ambiguous, the constitution check is borderline, or you'd be reaching to justify the "because Y" — invoke this skill instead. The guided path exists for exactly those cases.

## Validation Rules You MUST Enforce

- **Constitution validation is blocking.** If the decision violates a principle, refuse and surface the principle. Never silently log a violating decision.
- **No silent deletion.** Editing `specs/3_DECISIONS.md` is fine; deleting past lines is not. The only mutation to a prior line is the supersession annotation.
- **No bare "because we decided".** Rationale must reference a tradeoff, a constraint, or an external requirement.
- **No duplicate ID reuse.** Even retired IDs stay retired — never reassign `D-0042`.

## Output Contract

- `specs/3_DECISIONS.md`, append-only.
- `CLAUDE.md` pointer block presence verified (delegated to `ls-init`; this skill does not write `CLAUDE.md`).
- A short stdout report: new ID, entry text, constitution-check status, and (for supersede) the ID being replaced.

## What This Skill MUST NOT Do

- NEVER delete or rewrite the content of a past decision line. Strikethrough + annotation only.
- NEVER write to `CLAUDE.md` directly — pointer block ownership belongs to `ls-init`. If the pointer block is missing, instruct the user to run `/ls-init`.
- NEVER skip the constitution validation.
- NEVER let an entry exceed ~25 words. If it needs to, the user is documenting a design, not a decision — point them at `ls-intent` instead.
