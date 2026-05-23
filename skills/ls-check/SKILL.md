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

You also **derive each intent's `status`** from its outcome pass-counts and write the derived value back to the intent's frontmatter (`status`, `verdict_outcomes_passed`, `verdict_outcomes_passed_by_test`, `verdict_outcomes_total`, `verdict_checked_at`, and `closed`). The user never hand-writes `status: complete`.

Verification is mechanical: each SHALL is checked individually, not vibe-checked as a whole. When an outcome carries a `[test: <runner>:<target>]` citation, `ls-check` executes that test and uses the exit code as the verdict — exit 0 is the only path to a test-backed `pass`. Outcomes without a citation fall back to grep + LLM judgment, and the report marks them explicitly so the reader can tell which verdicts are test-executed and which are LLM-judged.

## Inputs

- The current working directory MUST contain `specs/INTENT/` with at least one `I-*-*/intent.md`. `specs/CONSTITUTION.md` is strongly recommended.
- Optional `--intent I-N` flag scopes the run to one intent (used by `ls-intent` after `new`/`refine`/`supersede`).
- Optional free-text scope hint from the user (e.g., "check the toggle feature") narrows the code surface for the run.
- Optional `--no-tests` flag skips test execution and falls back to grep + LLM judgment for every outcome (useful when the test suite is broken for unrelated reasons or the user wants a cheap dry-run). Citations are still parsed and reported as "skipped".

## Discovery

1. Glob `specs/INTENT/I-*-*/intent.md`. Read each one's frontmatter.
2. **Without `--intent`:** filter to non-terminal intents (`status not in {complete, superseded}`). Iterate each.
3. **With `--intent I-N`:** run on that one intent regardless of status. (This is how a regression on a previously-`complete` intent gets caught — and how a freshly-`new`'d draft gets its first verdict.)
4. If no intents match, refuse with a message naming which intents exist and what their statuses are. Suggest `/ls-intent new` if the tree is empty.

## Per-intent procedure

For each selected intent `I-N`:

1. **Read frontmatter and body.** Extract every EARS statement from the `## Outcome` section. Number them in order of appearance: `O-1`, `O-2`, …. For each `O-N`, also collect every `[test: <runner>:<target>]` marker that appears on the EARS line or in indented sub-bullets directly under it (until the next outcome bullet or section header).
2. **Read `specs/CONSTITUTION.md`** if present (read it once per ls-check run, not per intent). Number the principles by their existing IDs.
3. **Identify the code surface.** Use Glob/Grep to find files that plausibly implement the intent. Default surface: `src/`, `skills/`, `lib/`, plus any path the user named, plus this intent's own `experiments/` folder if it has been written to. If the project is a skill toolkit, the `SKILL.md` files themselves count as "code".
4. **For each `O-N`, classify code-drift.** The classification path depends on whether `O-N` carries a `[test: ...]` citation. Pick exactly one path:

   **Path A — test-backed** (`O-N` has ≥1 citation, and `--no-tests` was NOT passed):
   - For each citation, validate the runner is in the allowed set (`pytest`, `vitest`, `jest`, `cargo`, `go`, `npm`, `shell`). An unknown runner → classify the whole outcome `unverifiable (unknown runner: <name>)` and skip execution; do NOT silently fall back to grep — silently downgrading would hide a typo in the citation.
   - Reject whole-suite citations (e.g., `pytest:tests/` or `pytest:.` with no `::` or `-k` filter, `vitest:` with no args, `cargo:` with no test-name, `go:` with no `-run` pattern). Classify the outcome `unverifiable (whole-suite citation — one SHALL → one test)`. The same rule lives in `ls-intent`; this enforces it at check time.
   - **Pre-flight: greenfield check.** Before invoking the runner, resolve the target file portion of the citation (e.g., `tests/x.py` from `pytest:tests/x.py::test_y`). If the file does not exist on disk, classify the outcome `fail (test not found at <path>)` and skip execution. This is the pre-implementation signal — a missing cited test is evidence the work hasn't been done, distinct from a runner that crashed.
   - Otherwise, execute each citation via Bash, mapping to the command in the runner table (see `ls-intent`'s "Test citations" section). Use a 60-second per-test timeout by default; if the citation needs longer, the user must move it to a `shell:` citation that handles its own timeout. Capture exit code, elapsed time, and the last ~20 lines of stdout+stderr.
   - Combine results across the outcome's citations:
     - All citations exit 0 → `pass`. Cite the runner, target, and elapsed time in the report.
     - Any citation exits non-zero (test ran and failed) → `fail`. Cite the failing runner, target, exit code, and a stdout/stderr excerpt.
     - Any citation could not run at all (runner binary missing, syntax error before the test executed, timeout) → `unverifiable (test execution error: <message>)`. Do NOT classify as `fail` — a missing test runner is not evidence the SHALL is broken.

   **Path B — grep fallback** (`O-N` has no citation, OR `--no-tests` was passed):
   - Grep for keywords from the trigger and response. Classify as one of:
     - `pass` — implementation satisfies the SHALL. Cite the file:line where the satisfying behavior lives. **Always mark this verdict with a trailing `(no test citation)` flag** in the report — the verdict is LLM-judged, not test-executed, and the user should know.
     - `fail` — implementation contradicts or omits the SHALL. Cite the file:line where the contradiction lives, or note "no implementation found" and where you searched.
     - `unverifiable` — the SHALL is genuinely not mechanically checkable (e.g., a UX-feel claim). Flag it so the user can either rewrite the EARS or accept the limitation.
   - Emit a self-critique flag on every grep-fallback outcome (except when `--no-tests` was passed — the user opted out for this run): `O-N has no [test: ...] citation — re-invoke /ls-intent refine to add one.` This is the only place ls-check nudges the user back to ls-intent; we want the citation-coverage ratio to climb over time.
5. **For each `O-N`, check intent-drift.** Compare the most recent commit touching this intent's file (`git log -1 --format=%ct -- specs/INTENT/I-N-<slug>/intent.md`) against the most recent commit touching the code file you cited in step 4 (`git log -1 --format=%ct -- <file>`). Both sides are Unix timestamps (`%ct`), so the comparison is a single integer test — no date-string normalization needed. If the intent commit is strictly newer, flag `intent ahead` — the intent moved but the code didn't.
6. **Compute the verdict counts** (unverifiable is excluded from the total, per design):
   - `verdict_outcomes_total = count(O-N classified as pass or fail)`
   - `verdict_outcomes_passed = count(O-N classified as pass)`
   - `verdict_outcomes_passed_by_test = count(O-N classified as pass via the test-backed path)` — a strictly stronger signal than `verdict_outcomes_passed`; `passed_by_test ≤ passed` always holds. This is the metric the user should watch climb over time.
   - `verdict_checked_at = <now, ISO 8601 with Z>`
7. **Derive `status`:**
   - `complete` iff `verdict_outcomes_total > 0` AND `verdict_outcomes_passed == verdict_outcomes_total`
   - `in_progress` iff `verdict_outcomes_passed > 0` AND `verdict_outcomes_passed < verdict_outcomes_total`
   - `draft` otherwise (covers `_total == 0` and `_passed == 0`)
   - **Exception:** if the existing frontmatter `status` is `superseded`, leave it untouched and skip the closed/verdict writeback for this intent (you only got here because `--intent I-N` named it explicitly).
   - **All-unverifiable warning:** if the intent has outcomes but every one was classified `unverifiable` (so `_total == 0` while the body's `## Outcome` section is non-empty), status stays at `draft` and the intent can never reach `complete`. Emit a warning in the per-intent report block: `WARNING: all outcomes are unverifiable — re-invoke /ls-intent refine to make at least one outcome mechanically checkable.` Do not silently leave the user stuck.
   - **Weak-complete warning:** if `status` flips to `complete` this run AND `verdict_outcomes_passed_by_test < verdict_outcomes_total` (i.e., at least one outcome reached `pass` via grep + LLM judgment, not via test execution), emit a warning in the per-intent report block: `WARNING: I-N reached complete with <K>/<T> outcomes test-backed — the remaining <T-K> are LLM-judged. Add [test: ...] citations via /ls-intent refine to harden the verdict.` Status still flips (the contract is `_passed == _total`), but the gap is surfaced rather than hidden.
8. **Update `closed`:**
   - Flipping to `complete` (from anything else this run): set `closed` to today's ISO date (date, not full timestamp — humans read this).
   - Flipping away from `complete` (regression): set `closed: null`.
   - No flip: leave `closed` as-is.
9. **Write the updated frontmatter back to `intent.md`.** Frontmatter only — never touch the body (everything after the closing `---` is read-only here). Preserve key order, YAML formatting, and **any unrecognized keys** — other skills or future versions may add fields not enumerated in step 7's contract; leave them untouched rather than silently dropping them. **Skip the writeback entirely if no field would change.** Specifically: if the freshly-derived `status`, `closed`, `verdict_outcomes_passed`, `verdict_outcomes_passed_by_test`, and `verdict_outcomes_total` all match the existing values, do NOT update `verdict_checked_at` and do NOT rewrite the file. This prevents constant git churn from `/ls-check` runs that found no semantic change.

## Constitution-drift section

Run **once per ls-check invocation** (not per intent). For each principle, ask: does any part of the current code or any current EARS outcome (across all checked intents) violate this principle? Grep for the principle's keywords (e.g., a "static typing" principle ⇒ look for untyped surfaces). Classify each principle as `pass`, `fail`, or `not applicable to this scope`.

## Report format

Print one combined report to stdout. Do NOT write the report to a file — drift reports are ephemeral and tied to a specific moment in time.

```markdown
# ls-check report — YYYY-MM-DD

## I-1: <title>  [status: in_progress, 2/4 outcomes passing, 1/4 by test]

### Code drift
- [x] O-1: <EARS text> — pass (test). `pytest tests/test_foo.py::test_bar` exit 0 in 0.42s.
- [ ] O-2: <EARS text> — fail (test). `pytest tests/test_foo.py::test_baz` exit 1 in 0.18s. Tail:
      ```
      E       assert latency_ms < 200
      E       AssertionError: 247 not < 200
      ```
- [x] O-3: <EARS text> — pass (no test citation). Implemented at <file:line>. Flag: add `[test: ...]` via /ls-intent refine.
- [?] O-4: <EARS text> — unverifiable (test execution error: pytest: command not found).

### Intent drift
- O-2 — intent ahead. intent.md updated 2026-05-22; relevant code last touched 2026-04-30.

## I-2: <title>  [status: complete, 5/5 outcomes passing, 5/5 by test]

### Code drift
- [x] O-1: ... — pass (test). ...
... (one block per checked intent)

## Constitution drift
- [x] P-9 (EARS notation) — pass.
- [ ] P-14 (static typing) — fail. `src/foo.ts` uses `any` at line 42.

## Summary
Intents checked: 2. Status changes this run: I-2 in_progress → complete (closed 2026-05-23).
Across all intents: <N pass> (<M by test), <F fail>, <U unverifiable>, <D intent-ahead>.
Test-citation coverage: <P>/<T> outcomes have a [test: ...] marker (<pct>%).
```

The bracketed status header per intent shows the **newly derived** status, the overall verdict ratio (`_passed`/`_total`), and the test-backed ratio (`_passed_by_test`/`_total`) — the latter is the stronger signal and the one to push toward 100%.

Each outcome line MUST mark its verdict source explicitly: `pass (test)`, `pass (no test citation)`, `fail (test)`, `fail (no test citation — grep)`, or `unverifiable (<reason>)`. A reader scanning the report should never wonder whether a verdict came from a test or from grep.

## Test Execution Rules

- **Citations are run in order**, not parallelized. Per-intent test cost is bounded by the sum of timeouts (60s default per test), so a 5-outcome intent caps at 5 minutes worst-case. Users who need faster runs should narrow with `--intent I-N` rather than parallelizing — parallel test execution introduces ordering bugs that hide the very drift this skill is supposed to surface.
- **Each test runs in the repo root** (the same cwd `ls-check` was invoked in). If the project needs a different test cwd (monorepo subpackages, etc.), the citation MUST be a `shell:` runner that handles the `cd` itself. Do NOT auto-resolve cwd from the citation path — that's a guess, and guessing wrong silently passes the wrong test.
- **Environment is inherited.** ls-check does not strip env vars or activate virtualenvs. If a test needs a specific environment, set it before invoking `/ls-check`. The constitution is the right place to document required env (`Testing` bucket).
- **Test side effects are the user's problem.** The framework does NOT sandbox tests, mock the filesystem, or roll back DB writes. The constitution SHOULD carry a principle like "EARS-cited tests MUST be idempotent and side-effect-free" — `ls-intent` won't enforce that, but the user will feel the pain quickly if they violate it.
- **A flaky test is treated as `fail`, not `unverifiable`.** Exit codes are authoritative. If a test is flaky, the user must fix it or pin the seed — silently retrying would hide real regressions.
- **Constitution interaction.** If `specs/CONSTITUTION.md` declares an allowed runner whitelist narrower than the built-in set (e.g., "Testing: only pytest"), `ls-check` MUST honor it — a citation using a runner the constitution forbids is classified `unverifiable (constitution forbids runner: <name>)`. This is the one place a constitutional principle directly shapes ls-check's mechanics.

## Drift Classification Rules

- Be **specific**. Every `fail` MUST cite a file:line or an explicit "searched X, found nothing". Generic "this doesn't seem right" findings violate the EARS contract — the whole point of EARS is that drift maps to a precise SHALL.
- Be **honest about unverifiability**. If a SHALL is too vague to check (e.g., "THE SYSTEM SHALL feel responsive"), say so and recommend the user re-invoke `/ls-intent refine` to refine it.
- **Don't widen scope.** If the user asked for the toggle feature, don't audit the whole repo. Stay within the named scope unless the user opts in. Multi-intent runs are *by design* — they're not scope creep.
- **Don't fix.** This skill reports drift and writes the verdict frontmatter; it does not silently edit code, intent body content, or the constitution. Suggested remediations go in the report; applying them is the user's call.

## Edge Cases

- **No `specs/INTENT/` or empty directory** — refuse to run and tell the user to invoke `/ls-intent new` first.
- **No `specs/CONSTITUTION.md`** — proceed without the constitution-drift section, and note the omission in the report.
- **Intent has no `## Outcome` section or no EARS statements** — skip it in the multi-intent loop with NO frontmatter writeback (the intent's frontmatter, including `verdict_checked_at`, is left untouched). Continue with the other intents and name the skipped one in the report with a self-critique flag suggesting `/ls-intent refine`.
- **`--intent I-N` does not exist** — refuse, list existing IDs and statuses.
- **Malformed YAML frontmatter or missing `---` delimiters** — skip that intent in the multi-intent loop with NO writeback, note the parse error in the report, and suggest `/ls-intent refine` (or manual repair). Never partial-write a file whose frontmatter couldn't be parsed.
- **Legacy intent.md without a `status:` field** (e.g., a hand-created or pre-refactor file) — treat as if `status: draft`, run the full check, and produce a normal writeback (which will add the missing field). Do NOT crash. Other unrecognized legacy keys are preserved verbatim per step 9.
- **No code yet (greenfield)** — every `O-N` becomes `fail`. For test-backed outcomes the reason is `test not found at <path>`; for grep-fallback outcomes it's `no implementation found`. Status stays `draft`. That's a valid pre-implementation snapshot, not an error — the test paths in the citations double as a to-do list for the implementation.

## What This Skill MUST NOT Do

- NEVER edit body content of `intent.md` — frontmatter writeback only.
- NEVER edit code or the constitution.
- NEVER report drift without a specific citation (file:line, commit SHA, runner+target+exit-code, or "searched X, found nothing").
- NEVER summarize multiple SHALLs into a single overall pass/fail — every EARS statement gets its own line.
- NEVER widen scope beyond what the user asked for (free-text scope hint).
- NEVER auto-flip a `superseded` intent's status — that field is set by `/ls-intent supersede` and is terminal.
- NEVER silently fall back from the test-backed path to the grep path. If a citation can't be parsed, can't be executed, or names a forbidden runner, classify the outcome `unverifiable` with the precise reason — do NOT pretend grep was the plan.
- NEVER classify a test-backed outcome `pass` when the cited test wasn't actually executed. Exit code 0 from an actually-run process is the only path to a test-backed pass.
- NEVER classify a missing test file as `pass` or as `unverifiable`. A cited test that doesn't exist is `fail (test not found at <path>)` — that's the greenfield signal users rely on to drive implementation.
- NEVER retry a failing test to chase flakiness. Exit codes are authoritative; flakiness is a user-fixable bug.
