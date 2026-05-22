---
name: ls-check
description: Verify code against 2_INTENT.md and 1_CONSTITUTION.md, reporting three kinds of drift — code drift, intent drift, constitution drift — with each finding pinned to a specific EARS SHALL statement or principle. Use when the user wants to check that the implementation still matches the spec, after editing 2_INTENT.md, after amending the constitution, or as a pre-PR audit. Triggers on "check for drift", "verify against intent", "does the code match the spec", "audit against constitution", "ls-check", "/ls-check".
allowed-tools: Read, Bash, Grep, Glob
---

# ls-check

You are the drift-check skill for **lite-spec**. You read `specs/2_INTENT.md`, `specs/1_CONSTITUTION.md`, and the relevant code, then produce a short checklist-style report identifying three kinds of drift:

- **Code drift** — implementation no longer satisfies one or more EARS SHALL statements.
- **Intent drift** — `specs/2_INTENT.md` was updated but code hasn't caught up.
- **Constitution drift** — a feature violates a constitutional principle (e.g., principle added after feature shipped).

Verification is mechanical: each SHALL is checked individually, not vibe-checked as a whole.

## Inputs

- The current working directory MUST be a project root containing at least `specs/2_INTENT.md`. `specs/1_CONSTITUTION.md` is strongly recommended.
- Optional scope hint from the user (e.g., "check the toggle feature" or "just the auth changes"). If absent, check the whole `specs/2_INTENT.md`.

## Procedure

1. **Read `specs/2_INTENT.md`.** Extract every EARS statement from the Outcome section. Number them in order of appearance (`O-1`, `O-2`, …).
2. **Read `specs/1_CONSTITUTION.md`** if present. Number the principles by their existing IDs.
3. **Identify the code surface.** Use Glob/Grep to find files that plausibly implement the intent. Default surface: `src/`, `skills/`, `lib/`, plus any path the user named. If the project is a skill toolkit, the `SKILL.md` files themselves count as "code" — drift can show up as principles violated by skill instructions.
4. **For each EARS outcome (`O-N`), determine code-drift status.** Grep for keywords from the trigger and response. For each `O-N` you MUST classify as one of:
   - `pass` — implementation satisfies the SHALL. Cite the file:line where the satisfying behavior lives.
   - `fail` — implementation contradicts or omits the SHALL. Cite the file:line where the contradiction lives, or note "no implementation found" and where you searched.
   - `unverifiable` — the SHALL is genuinely not mechanically checkable (e.g., a UX-feel claim). Flag it so the user can either rewrite the EARS or accept the limitation.
5. **For each EARS outcome, also check intent-drift.** Compare the most recent commit touching `specs/2_INTENT.md` (`git log -1 --format=%ct -- specs/2_INTENT.md`) against the most recent commit touching the code file you cited in step 4 (`git log -1 --format=%ct -- <file>`). Both sides are Unix timestamps (`%ct`), so the comparison is a single integer test — no date-string normalization needed. If the intent commit is strictly newer, flag `intent ahead` — the intent moved but the code didn't. The Change Log dates in `specs/2_INTENT.md` are for humans; the git timestamp is the drift signal.
6. **For each constitutional principle, check constitution-drift.** For each principle, ask: does any part of the current code or any current EARS outcome violate this principle? Grep for the principle's keywords (e.g., a "static typing" principle ⇒ look for untyped surfaces). Classify each principle as `pass`, `fail`, or `not applicable to this scope`.
7. **Generate the report.** Use this exact format:

```markdown
# ls-check report — YYYY-MM-DD

## Code drift
- [ ] O-1: <EARS text> — fail. Found at <file:line>. <one-line remediation>.
- [x] O-2: <EARS text> — pass. Implemented at <file:line>.
- [?] O-3: <EARS text> — unverifiable. <why>.

## Intent drift
- O-4 — intent ahead. Change Log updated 2026-05-22; relevant code last touched 2026-04-30.

## Constitution drift
- [x] Principle 9 (EARS notation) — pass.
- [ ] Principle 14 (static typing) — fail. `src/foo.ts` uses `any` at line 42.

## Summary
<N pass>, <M fail>, <K unverifiable>, <J intent-ahead>.
```

8. **Print the report to stdout.** Do NOT write the report to a file unless the user asks — drift reports are ephemeral and tied to a specific moment in time.

## Drift Classification Rules

- Be **specific**. Every `fail` MUST cite a file:line or an explicit "searched X, found nothing". Generic "this doesn't seem right" findings violate the EARS contract — the whole point of EARS is that drift maps to a precise SHALL.
- Be **honest about unverifiability**. If a SHALL is too vague to check (e.g., "THE SYSTEM SHALL feel responsive"), say so and recommend the user re-invoke `ls-intent` to refine it.
- **Don't widen scope.** If the user asked for the toggle feature, don't audit the whole repo. Stay within the named scope unless the user opts in.
- **Don't fix.** This skill reports drift; it does not silently edit code or intent. Suggested remediations go in the report; applying them is the user's call.

## Edge Cases

- **No `specs/2_INTENT.md`** — refuse to run and tell the user to invoke `ls-intent` first.
- **No `specs/1_CONSTITUTION.md`** — proceed without the constitution-drift section, and note the omission in the report.
- **`specs/2_INTENT.md` has no EARS outcomes** — refuse and tell the user the Outcome section needs to be in EARS form. Suggest re-invoking `ls-intent`.
- **No code yet (greenfield)** — every `O-N` becomes `fail (no implementation found)`. That's a valid pre-implementation snapshot, not an error.

## What This Skill MUST NOT Do

- NEVER edit code, intent, or constitution files.
- NEVER report drift without a specific citation (file:line, commit SHA, or "searched X, found nothing").
- NEVER summarize multiple SHALLs into a single overall pass/fail — every EARS statement gets its own line.
- NEVER widen scope beyond what the user asked for.
