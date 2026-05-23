---
name: ls-check
description: Verify code against the open intents under specs/INTENT/ and specs/CONSTITUTION.md, reporting three kinds of drift — code drift, intent drift, constitution drift — with each finding pinned to a specific EARS SHALL statement or principle. Derives each intent's `status` from outcome pass-counts and writes it back to the intent.md frontmatter. Use when the user wants to check that the implementation still matches the spec, after editing any intent.md, after amending the constitution, or as a pre-PR audit. Triggers on "check for drift", "verify against intent", "does the code match the spec", "audit against constitution", "ls-check", "/ls-check".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# ls-check

You are the drift-check skill for **lite-spec**. You read every open intent under `specs/INTENT/`, the constitution at `specs/CONSTITUTION.md`, and the relevant code, then produce a short checklist-style report identifying three kinds of drift:

- **Code drift** — implementation no longer satisfies one or more EARS SHALL statements.
- **Intent drift** — an `intent.md` was updated but code hasn't caught up.
- **Constitution drift** — a feature violates a constitutional principle (e.g., principle added after feature shipped).

You also **derive each intent's `status`** from its outcome pass-counts and write the derived value back to the intent's frontmatter (`status`, `verdict_outcomes_passed`, `verdict_outcomes_total`, `verdict_checked_at`, and `closed`). The user never hand-writes `status: complete`.

Verification is mechanical: each SHALL is checked individually, not vibe-checked as a whole.

## Inputs

- The current working directory MUST contain `specs/INTENT/` with at least one `IT-*-*/intent.md`. `specs/CONSTITUTION.md` is strongly recommended.
- Optional `--intent IT-N` flag scopes the run to one intent (used by `ls-intent` after `new`/`refine`/`supersede`).
- Optional free-text scope hint from the user (e.g., "check the toggle feature") narrows the code surface for the run.

## Discovery

1. Glob `specs/INTENT/IT-*-*/intent.md`. Read each one's frontmatter.
2. **Without `--intent`:** filter to non-terminal intents (`status not in {complete, superseded}`). Iterate each.
3. **With `--intent IT-N`:** run on that one intent regardless of status. (This is how a regression on a previously-`complete` intent gets caught — and how a freshly-`new`'d draft gets its first verdict.)
4. If no intents match, refuse with a message naming which intents exist and what their statuses are. Suggest `/ls-intent new` if the tree is empty.

## Per-intent procedure

For each selected intent `IT-N`:

1. **Read frontmatter and body.** Extract every EARS statement from the `## Outcome` section. Number them in order of appearance: `O-1`, `O-2`, ….
2. **Read `specs/CONSTITUTION.md`** if present (read it once per ls-check run, not per intent). Number the principles by their existing IDs.
3. **Identify the code surface.** Use Glob/Grep to find files that plausibly implement the intent. Default surface: `src/`, `skills/`, `lib/`, plus any path the user named, plus this intent's own `experiments/` folder if it has been written to. If the project is a skill toolkit, the `SKILL.md` files themselves count as "code".
4. **For each `O-N`, classify code-drift:** grep for keywords from the trigger and response. Classify as one of:
   - `pass` — implementation satisfies the SHALL. Cite the file:line where the satisfying behavior lives.
   - `fail` — implementation contradicts or omits the SHALL. Cite the file:line where the contradiction lives, or note "no implementation found" and where you searched.
   - `unverifiable` — the SHALL is genuinely not mechanically checkable (e.g., a UX-feel claim). Flag it so the user can either rewrite the EARS or accept the limitation.
5. **For each `O-N`, check intent-drift.** Compare the most recent commit touching this intent's file (`git log -1 --format=%ct -- specs/INTENT/IT-N-<slug>/intent.md`) against the most recent commit touching the code file you cited in step 4 (`git log -1 --format=%ct -- <file>`). Both sides are Unix timestamps (`%ct`), so the comparison is a single integer test — no date-string normalization needed. If the intent commit is strictly newer, flag `intent ahead` — the intent moved but the code didn't.
6. **Compute the verdict counts** (unverifiable is excluded from the total, per design):
   - `verdict_outcomes_total = count(O-N classified as pass or fail)`
   - `verdict_outcomes_passed = count(O-N classified as pass)`
   - `verdict_checked_at = <now, ISO 8601 with Z>`
7. **Derive `status`:**
   - `complete` iff `verdict_outcomes_total > 0` AND `verdict_outcomes_passed == verdict_outcomes_total`
   - `in_progress` iff `verdict_outcomes_passed > 0` AND `verdict_outcomes_passed < verdict_outcomes_total`
   - `draft` otherwise (covers `_total == 0` and `_passed == 0`)
   - **Exception:** if the existing frontmatter `status` is `superseded`, leave it untouched and skip the closed/verdict writeback for this intent (you only got here because `--intent IT-N` named it explicitly).
8. **Update `closed`:**
   - Flipping to `complete` (from anything else this run): set `closed` to today's ISO date (date, not full timestamp — humans read this).
   - Flipping away from `complete` (regression): set `closed: null`.
   - No flip: leave `closed` as-is.
9. **Write the updated frontmatter back to `intent.md`.** Frontmatter only — never touch the body. Preserve key order and YAML formatting.

## Constitution-drift section

Run **once per ls-check invocation** (not per intent). For each principle, ask: does any part of the current code or any current EARS outcome (across all checked intents) violate this principle? Grep for the principle's keywords (e.g., a "static typing" principle ⇒ look for untyped surfaces). Classify each principle as `pass`, `fail`, or `not applicable to this scope`.

## Report format

Print one combined report to stdout. Do NOT write the report to a file — drift reports are ephemeral and tied to a specific moment in time.

```markdown
# ls-check report — YYYY-MM-DD

## IT-1: <title>  [status: in_progress, 2/4 outcomes passing]

### Code drift
- [x] O-1: <EARS text> — pass. Implemented at <file:line>.
- [ ] O-2: <EARS text> — fail. Found at <file:line>. <one-line remediation>.
- [?] O-3: <EARS text> — unverifiable. <why>.

### Intent drift
- O-4 — intent ahead. intent.md updated 2026-05-22; relevant code last touched 2026-04-30.

## IT-2: <title>  [status: complete, 5/5 outcomes passing]

### Code drift
- [x] O-1: ... — pass. ...
... (one block per checked intent)

## Constitution drift
- [x] Principle 9 (EARS notation) — pass.
- [ ] Principle 14 (static typing) — fail. `src/foo.ts` uses `any` at line 42.

## Summary
Intents checked: 2. Status changes this run: IT-2 in_progress → complete (closed 2026-05-23).
Across all intents: <N pass>, <M fail>, <K unverifiable>, <J intent-ahead>.
```

The bracketed status header per intent shows the **newly derived** status (post-writeback) and the verdict ratio (`_passed`/`_total`, where `_total` excludes unverifiable).

## Drift Classification Rules

- Be **specific**. Every `fail` MUST cite a file:line or an explicit "searched X, found nothing". Generic "this doesn't seem right" findings violate the EARS contract — the whole point of EARS is that drift maps to a precise SHALL.
- Be **honest about unverifiability**. If a SHALL is too vague to check (e.g., "THE SYSTEM SHALL feel responsive"), say so and recommend the user re-invoke `/ls-intent refine` to refine it.
- **Don't widen scope.** If the user asked for the toggle feature, don't audit the whole repo. Stay within the named scope unless the user opts in. Multi-intent runs are *by design* — they're not scope creep.
- **Don't fix.** This skill reports drift and writes the verdict frontmatter; it does not silently edit code, intent body content, or the constitution. Suggested remediations go in the report; applying them is the user's call.

## Edge Cases

- **No `specs/INTENT/` or empty directory** — refuse to run and tell the user to invoke `/ls-intent new` first.
- **No `specs/CONSTITUTION.md`** — proceed without the constitution-drift section, and note the omission in the report.
- **Intent has no `## Outcome` section or no EARS statements** — refuse for that intent (skip it in the multi-intent loop), continue with the others, and surface a self-critique flag suggesting `/ls-intent refine` on the affected ID.
- **`--intent IT-N` does not exist** — refuse, list existing IDs and statuses.
- **No code yet (greenfield)** — every `O-N` becomes `fail (no implementation found)`. Status stays `draft`. That's a valid pre-implementation snapshot, not an error.

## What This Skill MUST NOT Do

- NEVER edit body content of `intent.md` — frontmatter writeback only.
- NEVER edit code or the constitution.
- NEVER report drift without a specific citation (file:line, commit SHA, or "searched X, found nothing").
- NEVER summarize multiple SHALLs into a single overall pass/fail — every EARS statement gets its own line.
- NEVER widen scope beyond what the user asked for (free-text scope hint).
- NEVER auto-flip a `superseded` intent's status — that field is set by `/ls-intent supersede` and is terminal.
