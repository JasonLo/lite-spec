---
name: spec-decisions
description: Append a one-line decision entry to specs/DECISIONS.md, or supersede an existing one. Use when the user has made a non-trivial choice during development (architecture, library, approach, scope cut) and wants it captured durably. Triggers on "log a decision", "record this choice", "add to DECISIONS.md", "we decided X", "supersede decision", "/spec-decisions".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# spec-decisions

You are the decisions skill for **lite-spec**. You maintain `specs/DECISIONS.md` — an append-only log of non-trivial decisions with rationale. Each new entry is a single line:

```
- **D-N:** Decided X because Y (YYYY-MM-DD). [intent: I-N]
```

The trailing `[intent: I-N]` tag links the decision to the intent it was made under, enabling `grep '\[intent: I-2\]' specs/DECISIONS.md` to enumerate one intent's decisions. Legacy untagged lines from before the tag rule are valid on read but never re-emitted.

When a decision is reversed, supersession is captured as a structured tag pair — `[supersedes: D-N]` on the new entry and `[superseded-by: D-M, YYYY-MM-DD]` on the struck-through prior entry. The pair mirrors the `superseded_by:` field on `intent.md` frontmatter and makes the chain grep-able from either end. See **Supersession tag pair** below for the full grammar.

This skill has two modes: **append** (a new decision) and **supersede** (a past decision is being reversed).

## Inputs

- The current working directory MUST be a project root.
- A description of the decision from the user (the "X") and a reason (the "Y").
- Optional `--intent I-N` flag to pin the tag explicitly.
- If `specs/CONSTITUTION.md` exists, you MUST read it and validate the decision against it.

## Resolving the `[intent: I-N]` tag

Every new entry MUST carry an `[intent: I-N]` tag. Resolve the tag in this order:

1. If `--intent I-N` is passed, use it. If no folder matches `specs/INTENT/I-N-*/`, refuse and list existing IDs.
2. Otherwise, glob `specs/INTENT/I-*-*/intent.md` and read each frontmatter `status`. Collect those with `status` in `{draft, in_progress}` — the **open** intents.
   - Exactly one open intent ⇒ use its ID. Report the auto-fill choice in the run output.
   - Zero open intents ⇒ refuse and tell the user to invoke `/spec-intent new` first (or pass `--intent I-N` to tag against a `complete` intent if that's genuinely what they want).
   - Multiple open intents ⇒ prompt the user for `--intent I-N`. Do NOT guess.

## Mode 1 — Append

1. **Read the constitution.** If `specs/CONSTITUTION.md` exists, read it. Cross-check the proposed decision against every principle.
2. **Read `specs/DECISIONS.md`.** If it doesn't exist, create it (creating specs/ first if needed) with the header from [DECISIONS_HEADER.template.md](DECISIONS_HEADER.template.md) (sibling of this SKILL.md).
3. **Pick the next ID.** Scan existing `D-N` IDs (tagged or untagged) and use the next sequential number (`max + 1`), no zero-padding — same shape as `I-N` intents and `P-N` principles.
4. **Resolve the `[intent: I-N]` tag** using the rule above.
5. **Deduplicate.** Grep `specs/DECISIONS.md` for keywords from the proposed decision. The grep MUST match both tagged and legacy untagged entries — do not assume the tag suffix exists on read. **Exclude struck-through entries** (lines starting with `- ~~`): those have already been reversed via supersession and are NOT candidates for duplicate-of-current. If a non-struck near-duplicate exists, surface it and ask the user whether to (a) skip — the choice is already recorded, (b) supersede the prior entry (switch to supersede mode), or (c) append anyway because the new entry is meaningfully different.
6. **Validate against the constitution.** If the decision would violate a principle, refuse and tell the user which principle is blocking. They MUST either revise the decision or invoke `/spec-constitution` to amend the principle.
7. **Check durability.** The entry MUST still make sense 6 months later. If the "because Y" reduces to "because we wanted to" or "because it's better", push back and ask for a concrete tradeoff (what was the alternative, what made this one win). If the user genuinely can't articulate a tradeoff, the decision probably isn't durable enough to log — say so.
8. **Aim for under 25 words** (excluding the `[intent: I-N]` suffix). A decision entry is one sentence, not a paragraph. If the rationale needs more, link to an intent or a doc rather than expanding inline.
9. **Append** the entry to `specs/DECISIONS.md`:

   ```
   - **D-N:** Decided X because Y (YYYY-MM-DD). [intent: I-N]
   ```

10. **Check the `CLAUDE.md` pointer block.** Grep `CLAUDE.md` at the repo root for the marker `<!-- lite-spec:pointer-block:start -->`. If the marker is present, the pointer block is already wired; do nothing. If the marker is missing (or `CLAUDE.md` itself is missing), tell the user to run `/spec-init` to wire `CLAUDE.md`. Do NOT write any pointer text from this skill — `spec-init` is the single source of truth for `CLAUDE.md`.
11. **Report** the new ID, the entry text including the resolved tag, how the tag was chosen (flag / auto / prompt), and confirmation that the constitution check passed. End the report with `Next: /spec-check --intent I-N` if the tagged intent's `status` is `draft` or `in_progress` (a logged decision usually implies code that should be re-verified against the intent). If the tag points at a `complete` or `superseded` intent, omit the `Next:` line. Follows the Handoff convention documented in `spec-init`.

## Mode 2 — Supersede

1. **Identify the prior entry.** The user MUST name the ID being superseded (e.g., `D-42`). If they don't, ask. Then read that line. If the line is already struck through or carries `[superseded-by: D-M, ...]` (or a legacy `[superseded by D-M, ...]` marker), refuse — a decision can be superseded only once. Walk the chain forward (grep for the successor's ID) and tell the user to supersede the current head instead.
2. **Pick the next ID** for the new entry.
3. **Resolve the `[intent: I-N]` tag** for the new entry (the struck-through prior entry is left as-is — never retroactively tag legacy lines).
4. **Run the same checks** as append mode (constitution, deduplication against *other* entries, durability).
5. **Strike the prior entry inline** with markdown strikethrough plus a structured `[superseded-by: D-N, YYYY-MM-DD]` tag appended **outside** the strikethrough:
   ```
   - ~~**D-42:** Decided REST because X (2026-01-10). [intent: I-3]~~ [superseded-by: D-73, 2026-05-23]
   ```
   NEVER delete the original text. Strikethrough preserves history while making current state unambiguous. If the prior entry carries an `[intent: ...]` tag, leave it inside the strikethrough — do not retag. The `[superseded-by: ...]` tag lives outside the `~~` so it can be grepped without matching content of unrelated decisions that happen to mention the word "superseded".
6. **Append the new entry** with an explicit `[supersedes: D-N]` tag alongside the `[intent: I-N]` tag:
   ```
   - **D-73:** Switched to GraphQL because <reason> (2026-05-23). [intent: I-N] [supersedes: D-42]
   ```
   The new entry's rationale stands on its own — do NOT lead with "Supersedes D-42 —" prose; the structured tag carries that link. The two tags are independent: `[intent: I-N]` is always required on new entries, `[supersedes: D-N]` only on supersessions. Order them `[intent: ...] [supersedes: ...]` for consistency.
7. **Report** both entries, how the new tag was chosen, the `[supersedes: D-N]` link, and the constitution-check result. End the report with `Next: /spec-check --intent I-N` if the new entry's tagged intent is `draft` or `in_progress` (supersession reverses a prior choice — code almost certainly needs to follow). Otherwise omit the `Next:` line. Follows the Handoff convention documented in `spec-init`.

## Supersession tag pair

The supersession chain is captured as two paired tags, mirroring the `superseded_by:` field on intent frontmatter so the relationship is grep-able from either end:

| Side | Tag | Lives on | Example |
|---|---|---|---|
| Successor | `[supersedes: D-N]` | the new (active) entry, trailing the rationale | `... (2026-05-23). [intent: I-7] [supersedes: D-42]` |
| Predecessor | `[superseded-by: D-N, YYYY-MM-DD]` | the struck-through prior entry, **outside** the `~~` | `~~- **D-42:** ...~~ [superseded-by: D-73, 2026-05-23]` |

**Grammar rules:**

- The successor tag carries only the predecessor ID — no date. The date already lives on the predecessor's `[superseded-by: ...]` tag and in the new entry's own `(YYYY-MM-DD)` clause.
- The predecessor tag carries both ID and date — the date answers "when was this reversed?" without needing to find the successor first.
- IDs in both tags refer to entries within the same `DECISIONS.md`; cross-file references are not supported.
- A decision MAY be superseded only once. If `D-42` already carries `[superseded-by: D-73, ...]`, refuse to supersede `D-42` again — instruct the user to supersede `D-73` instead (transitively, the chain becomes `D-42 → D-73 → D-99`).
- Both tags pair like `[intent: I-N]` for grep ergonomics — single keyword, colon-delimited value, square brackets. `grep '\[supersedes: D-42\]'` finds the successor of `D-42`; `grep '\[superseded-by: D-73,'` finds the predecessor of `D-73`.
- Legacy prose-form supersessions (`Supersedes D-N —` inline in the entry, or `[superseded by D-N, date]` without the colon on the predecessor) are valid on read but never re-emitted. Do NOT migrate legacy entries to the new tag form — that would mutate append-only history.

## Reader contract

`specs/DECISIONS.md` has two reading modes, and consumers — humans grepping for context, other skills loading the log, or agents answering "what stack did we settle on?" — MUST distinguish them:

- **"What is currently true" mode** (default for almost every read). **Skip struck-through entries** (`- ~~...~~`); they have been reversed. To find the active head from a struck-through entry, follow its `[superseded-by: D-N, date]` tag forward. A grep filter that excludes lines matching `^- ~~` returns only the currently-authoritative set. This matches how `spec-check` treats `status: superseded` intents — terminal, skipped by default.
- **"Full history" mode** (audits, post-mortems, decision-archaeology). Read every line, including struck-through entries. The supersession chain is preserved precisely so an auditor can replay the sequence of choices in order.

The struck-through wrapper (`- ~~...~~`) is the load-bearing signal — it is markdown-visible AND grep-distinguishable AND tag-paired. A reader that ignores it will treat reversed decisions as authoritative; a reader that respects it gets a clean view of current state for free. Always prefer the wrapper as the primary skip-filter; the tag pair is the chain-walking aid, not the filter.

`spec-decisions` itself follows the reader contract in two places: dedup excludes struck-through entries (Mode 1 step 5 and Direct writes rule 4) so duplicates are detected against the active set, not against reversed history.

## Direct writes (without invoking this skill)

This skill is the **guided path** — it elicits, deduplicates, checks durability, resolves the intent tag, and reports a constitution-validation result. But `specs/DECISIONS.md` is agent-writable by design — AI agents MAY also write to it directly when speed matters, subject to these rules:

1. **Read the constitution first.** If `specs/CONSTITUTION.md` exists, cross-check the proposed entry against every principle. If it violates a principle, do not write — surface the conflict and stop.
2. **Resolve the `[intent: I-N]` tag** using the same rule as the guided path: explicit flag wins, else single open intent ⇒ infer, else escalate to the guided path. Direct writes MUST carry the tag — no untagged new entries.
3. **Follow the format spec exactly.** `- **D-N:** Decided X because Y (YYYY-MM-DD). [intent: I-N]` — sequential integer ID with no zero-padding (scan existing entries for `max + 1`; existing IDs may be tagged or untagged — either counts), entry under 25 words excluding the tag, rationale must reference a tradeoff/constraint/external requirement (no bare "because we decided" or "because it's better").
4. **Dedup against existing entries.** Grep `specs/DECISIONS.md` for keywords from the proposed decision; match both tagged and untagged lines, but **exclude struck-through entries** (lines starting with `- ~~`, which have already been reversed). If a non-struck near-duplicate exists, do not write — either skip (the choice is already logged) or follow the supersession path (rule 6). When the duplicate call is ambiguous, escalate to this skill's guided path instead.
5. **Never log phantom commitments.** Only record decisions settled *with the human in the current conversation* — made by the human, or proposed by AI and explicitly accepted by the human. Autonomous AI choices made without explicit human assent belong in chat or a PR description, not in `DECISIONS.md`.
6. **Supersession via direct write is allowed.** Follow Mode 2 steps 5–6: strike the prior entry and append `[superseded-by: D-N, YYYY-MM-DD]` **outside** the `~~`, then append the new entry with `[intent: I-N] [supersedes: D-N]` tags trailing the rationale. Never delete a prior line. Never lead the new entry with "Supersedes D-N —" prose — the structured tag is the link.
7. **Append-only history still applies.** Editing the content of an existing decision line is forbidden; the only mutations are (a) appending the `[superseded-by: ...]` tag outside the `~~` and (b) wrapping the original line in strikethrough. Never retroactively add `[intent: ...]` or `[supersedes: ...]` tags to legacy entries — legacy prose-form supersessions (`Supersedes D-N —` inline) are valid on read but never re-emitted in the new format.

When in doubt — durability is unclear, the human's position is ambiguous, the constitution check is borderline, the intent tag is ambiguous, or you'd be reaching to justify the "because Y" — invoke this skill instead. The guided path exists for exactly those cases.

## Validation Rules You MUST Enforce

- **Constitution validation is blocking.** If the decision violates a principle, refuse and surface the principle. Never silently log a violating decision.
- **Every new entry carries `[intent: I-N]`.** Resolved via flag, single-open auto-pick, or prompt. Legacy untagged entries are valid on read but never re-emitted; never retroactively tag them.
- **Every supersession carries the `[supersedes: D-N]` / `[superseded-by: D-M, date]` tag pair.** Both sides MUST be written in the same operation — never write one without the other. Legacy prose-form supersessions are valid on read but never re-emitted in the new format.
- **A decision is superseded only once.** If the target already carries `[superseded-by: ...]`, refuse and direct the user to the current head of the chain.
- **No silent deletion.** Editing `specs/DECISIONS.md` is fine; deleting past lines is not. The only mutations to a prior line are wrapping it in `~~` and appending the `[superseded-by: ...]` tag outside the strikethrough.
- **No bare "because we decided".** Rationale must reference a tradeoff, a constraint, or an external requirement.
- **No duplicate ID reuse.** Even retired IDs stay retired — never reassign `D-42`.

## Output Contract

- `specs/DECISIONS.md`, append-only.
- `CLAUDE.md` pointer block presence verified (delegated to `spec-init`; this skill does not write `CLAUDE.md`).
- A short stdout report: new ID, entry text including resolved `[intent: I-N]` tag (and `[supersedes: D-N]` tag for supersede mode), how the intent tag was chosen, constitution-check status, and (for supersede) the predecessor ID with its newly-appended `[superseded-by: D-N, date]` annotation.

## What This Skill MUST NOT Do

- NEVER delete or rewrite the content of a past decision line. Strikethrough + `[superseded-by: ...]` tag only.
- NEVER retroactively add `[intent: I-N]`, `[supersedes: D-N]`, or `[superseded-by: D-N, ...]` tags to legacy entries. Legacy prose-form supersessions stay as they are.
- NEVER supersede a decision twice. If the target already carries `[superseded-by: ...]`, walk the chain forward and supersede the current head instead.
- NEVER place the `[superseded-by: ...]` tag inside the `~~` strikethrough — it lives outside so grep can find it without false matches on unrelated text.
- NEVER write to `CLAUDE.md` directly — pointer block ownership belongs to `spec-init`. If the pointer block is missing, instruct the user to run `/spec-init`.
- NEVER skip the constitution validation.
- NEVER let an entry exceed ~25 words (excluding the tags). If it needs to, the user is documenting a design, not a decision — point them at `/spec-intent refine` instead.
