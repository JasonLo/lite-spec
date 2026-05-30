---
name: spec-check
description: Verify code against the open intents under specs/INTENT/ and specs/CONSTITUTION.md and report drift. Use when the user wants to check that the implementation still matches the spec, after editing any intent.md, after amending the constitution, or as a pre-PR audit. Triggers on "check for drift", "verify against intent", "does the code match the spec", "audit against constitution", "spec-check", "/spec-check".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent
---

# spec-check

You are the drift-check skill for **lite-spec**. You read every open intent under `specs/INTENT/`, the constitution at `specs/CONSTITUTION.md`, and the relevant code, then produce a short checklist-style report identifying three kinds of drift:

- **Code drift** — implementation no longer satisfies one or more EARS SHALL statements.
- **Intent drift** — an `intent.md` was updated but code hasn't caught up.
- **Constitution drift** — a feature violates a constitutional principle (e.g., principle added after feature shipped).

You also **derive each intent's `status`** from its outcome pass-counts and write the derived value back to the intent's frontmatter (`status`, `verdict_outcomes_passed`, `verdict_outcomes_passed_by_test`, `verdict_outcomes_total`, `verdict_checked_at`, and `closed`). The user never hand-writes `status: complete`.

Verification is mechanical: each SHALL is checked individually, not vibe-checked as a whole. When an outcome carries a `[test: <runner>:<target>]` citation, `spec-check` executes it. Two flavors of runner exist:

- **Process runners** (`pytest`, `vitest`, `jest`, `cargo`, `go`, `shell`) — `spec-check` invokes them via Bash; exit code 0 is the only path to a test-backed `pass`.
- **Agent runner** (`agent:<path-to-prompt-file>`) — `spec-check` spawns a subagent, hands it the prompt file plus the EARS line plus scope hints, parses a structured verdict block, and reports `pass`, `fail`, or `unverifiable`. Use this only for SHALLs that genuinely can't be checked by a normal test (UX claims, doc structure, narrative consistency).

Outcomes without any `[test: ...]` citation are classified `unverifiable` — there is no grep + LLM inline fallback. To drive a SHALL to `pass`, the user adds a citation via `/spec-intent refine`.

## Inputs

- The current working directory MUST contain `specs/INTENT/` with at least one `I-*-*/intent.md`. `specs/CONSTITUTION.md` is strongly recommended.
- Optional `--intent I-N` flag scopes the run to one intent (used by `spec-intent` after `new`/`refine`/`supersede`).
- Optional free-text scope hint from the user (e.g., "check the toggle feature") narrows the code surface for the run.
- Optional `--no-tests` flag skips **all** runner execution (both process and agent runners). Citations are still parsed; every outcome with a citation is reported as `skipped (--no-tests)`, and outcomes with no citation remain `unverifiable`. With `--no-tests` no outcome can reach `pass`; the run is intentionally read-only and exists for fast structural sanity-checks (citation parseability, frontmatter validity, intent-ahead drift) without paying the cost of test or agent execution.
- Optional `--no-agents` flag skips only the agent runner. Process runners still execute. Useful when the user wants a fast deterministic run that ignores LLM-graded outcomes. With `--no-agents`, every `agent:` citation is reported as `skipped (--no-agents)`, and the outcome's verdict is `unverifiable (agent skipped)`.

## Discovery

1. Glob `specs/INTENT/I-*-*/intent.md`. Read each one's frontmatter.
2. **Without `--intent`:** filter to non-terminal intents (`status not in {complete, superseded}`). Iterate each.
3. **With `--intent I-N`:** run on that one intent regardless of status. (This is how a regression on a previously-`complete` intent gets caught — and how a freshly-`new`'d draft gets its first verdict.)
4. If no intents match, refuse with a message naming which intents exist and what their statuses are. Suggest `/spec-intent new` if the tree is empty.

## Per-intent procedure

For each selected intent `I-N`:

1. **Read frontmatter and body.** Extract every EARS statement from the `## Outcome` section. Number them in order of appearance: `O-1`, `O-2`, …. For each `O-N`, also collect every `[test: <runner>:<target>]` marker that appears on the EARS line or in indented sub-bullets directly under it (until the next outcome bullet or section header).
2. **Read `specs/CONSTITUTION.md`** if present (read it once per spec-check run, not per intent). Number the principles by their existing IDs.
3. **Identify the code surface.** Use Glob/Grep to find files that plausibly implement the intent. Default surface: `src/`, `skills/`, `lib/`, plus any path the user named, plus this intent's own `experiments/` folder if it has been written to. If the project is a skill toolkit, the `SKILL.md` files themselves count as "code".
4. **For each `O-N`, classify code-drift.** The path is determined by whether `O-N` carries any `[test: ...]` citation. Pick exactly one:

   **No citation at all** — classify the outcome `unverifiable (no test citation)`. Emit a self-critique flag in the report: `O-N has no [test: ...] citation — re-invoke /spec-intent refine to add one (process runner, or agent:<prompt-path> for SHALLs that can't be checked programmatically).` This is the only nudge spec-check sends back toward spec-intent for citation coverage; the goal is the by-test + by-agent ratio climbing over time.

   **Citation present** — validate every citation's runner against the allowed set: `pytest`, `vitest`, `jest`, `cargo`, `go`, `shell`, `agent`. An unknown runner → classify the whole outcome `unverifiable (unknown runner: <name>)` and skip execution; do NOT silently fall back — silently downgrading would hide a typo in the citation. Then split each citation by runner family and apply the rules below.

   **A1. Process runners** (`pytest` / `vitest` / `jest` / `cargo` / `go` / `shell`):
   - Reject whole-suite citations (e.g., `pytest:tests/` or `pytest:.` with no `::` or `-k` filter, `vitest:` with no args, `cargo:` with no test-name, `go:` with no `-run` pattern). Classify the outcome `unverifiable (whole-suite citation — one SHALL → one test)`. The same rule lives in `spec-intent`; this enforces it at check time.
   - **Pre-flight: greenfield check.** Before invoking the runner, resolve the target file portion of the citation (e.g., `tests/x.py` from `pytest:tests/x.py::test_y`). If the file does not exist on disk, classify the outcome `fail (test not found at <path>)` and skip execution. This is the pre-implementation signal — a missing cited test is evidence the work hasn't been done, distinct from a runner that crashed.
   - Otherwise, execute each citation via Bash, mapping to the command in the runner table (see `spec-intent`'s "Test citations" section). Use a 60-second per-test timeout by default; if the citation needs longer, the user must move it to a `shell:` citation that handles its own timeout. Capture exit code, elapsed time, and the last ~20 lines of stdout+stderr.

   **A2. Agent runner** (`agent:<path-to-prompt-file>`):
   - Validate the target is a path string with no shell metacharacters (`;`, `|`, `&`, backticks, `$(`). A citation that contains shell punctuation is classified `unverifiable (malformed agent citation: <target>)` — the agent runner takes a path, not a shell command.
   - Validate the path is **inside the repo root** (no `../` escapes, no absolute paths outside cwd, no symlinks pointing outside). A path outside the repo is classified `unverifiable (agent prompt path outside repo: <path>)`. Recommended convention: `specs/INTENT/I-N-<slug>/checks/<name>.md` — co-located with the intent so the prompt travels with the spec.
   - **Pre-flight: greenfield check.** If the prompt file does not exist, classify `fail (agent prompt not found at <path>)`. Treated as fail, not unverifiable — parallel to the process-runner "test not found" greenfield signal.
   - If the prompt file exists but is empty (zero bytes or whitespace-only), classify `unverifiable (agent prompt empty at <path>)`. An empty prompt would force the subagent to guess what to check.
   - **Honor the constitution whitelist.** If `specs/CONSTITUTION.md` declares an allowed-runner whitelist and `agent` is not in it, classify `unverifiable (constitution forbids runner: agent)`. Same mechanism as any other runner.
   - **Honor `--no-agents` and `--no-tests`.** If either flag is set, classify the citation as `skipped (--no-agents)` or `skipped (--no-tests)` and proceed to combine results.
   - Otherwise, spawn a subagent (mechanics in "Agent Runner Mechanics" below). Use a 5-minute timeout. Parse the structured verdict block. Possible outcomes per citation:
     - Subagent returns `verdict: pass` with 1–3 file:line citations and a reason → contributes a `pass` from this citation.
     - Subagent returns `verdict: fail` with 1–3 file:line citations and a reason → contributes a `fail`.
     - Subagent returns `verdict: unverifiable` with a reason → contributes `unverifiable (agent: <reason>)`.
     - Subagent reply is malformed (missing required fields, schema violation, non-JSON when JSON expected) → contributes `unverifiable (agent reply malformed: <details>)`. Do NOT retry on malformed; one shot per check, per the "no flakiness retry" rule.
     - Subagent invocation timed out → contributes `unverifiable (agent timed out after 5 min)`.
     - Subagent invocation failed at API level (spawn error) → contributes `unverifiable (agent invocation error: <message>)`.

   **Combining results across an outcome's citations** (works for any mix of process + agent + skipped):
   - All citations contribute `pass` → outcome is `pass`. The **strength-source label** records the strongest signal that backed the verdict: if at least one contributing citation was a process runner, mark `pass (test)`; otherwise (all-agent), mark `pass (agent)`. Process runners always upgrade the label because a process runner is the strongest signal.
   - Any citation contributes `fail` → outcome is `fail`. Cite the failing runner in the report. If the failing runner is `agent`, include the subagent's reason and its file:line citations in the report excerpt. If both a process runner and an agent disagreed (one passed, the other failed), the failing source wins the label — disagreement is itself the signal.
   - All citations contributed `unverifiable` or `skipped` (at least one was `skipped`, none was `pass` or `fail`) → outcome is `unverifiable (skipped)` or `unverifiable (<reason>)` — preserve the most specific reason.
5. **For each `O-N`, check intent-drift.** Compare the most recent commit touching this intent's file (`git log -1 --format=%ct -- specs/INTENT/I-N-<slug>/intent.md`) against the most recent commit touching the code file you cited in step 4 (`git log -1 --format=%ct -- <file>`). Both sides are Unix timestamps (`%ct`), so the comparison is a single integer test — no date-string normalization needed. If the intent commit is strictly newer, flag `intent ahead` — the intent moved but the code didn't.
6. **Compute the verdict counts** (unverifiable and skipped are excluded from the total, per design):
   - `verdict_outcomes_total = count(O-N classified as pass or fail)`. Unverifiable, skipped, and intent-ahead are excluded — the total reflects only what was actually graded.
   - `verdict_outcomes_passed = count(O-N classified as pass)` (any source).
   - `verdict_outcomes_passed_by_test = count(O-N classified as pass where the strength-source label is test)`. Strictest signal.
   - **Invariant:** `0 ≤ verdict_outcomes_passed_by_test ≤ verdict_outcomes_passed ≤ verdict_outcomes_total`. If the count math ever violates this invariant, abort the writeback for this intent and surface a `BUG:` line in the report — never persist a broken ladder.
   - `verdict_checked_at = <now, ISO 8601 with Z>`.
7. **Derive `status`:**
   - `complete` iff `verdict_outcomes_total > 0` AND `verdict_outcomes_passed == verdict_outcomes_total`
   - `in_progress` iff `verdict_outcomes_passed > 0` AND `verdict_outcomes_passed < verdict_outcomes_total`
   - `draft` otherwise (covers `_total == 0` and `_passed == 0`)
   - **Exception:** if the existing frontmatter `status` is `superseded`, leave it untouched and skip the closed/verdict writeback for this intent (you only got here because `--intent I-N` named it explicitly).
   - **All-unverifiable note (the lite path):** if the intent has outcomes but every one was classified `unverifiable` (so `_total == 0` while the body's `## Outcome` section is non-empty), status rests at `draft`. **This is a valid resting state, not an error** — the *lite path*, where the intent is a spec you and Claude read for context rather than one that's mechanically graded. Frame it as an informational note, not a warning, so the path forward is discoverable without implying the user did something wrong. Emit in the per-intent report block: `NOTE: I-N has outcomes but no [test: ...] citations, so it rests at draft — the lite path, a perfectly fine choice. To make it gradeable and let status climb toward complete, add a citation via /spec-intent refine; for a SHALL that can't be a process-runner test, cite an agent prompt: [test: agent:specs/INTENT/I-N-<slug>/checks/<name>.md].` Do not nag — surface the note once and move on.
   - **Weak-complete warning:** if `status` flips to `complete` this run AND `verdict_outcomes_passed_by_test < verdict_outcomes_total`, the verdict ladder is incomplete. With Path B removed, every `pass` is either test-backed or agent-backed — nothing else exists. Emit a warning in the per-intent report block: `WARNING: I-N reached complete with <K>/<T> outcomes test-backed; the remaining <T-K> are agent-backed. Consider promoting agent-backed outcomes to a real test where feasible via /spec-intent refine.` Status still flips (the contract is `_passed == _total`), but the ladder gap is surfaced rather than hidden.
8. **Update `closed`:**
   - Flipping to `complete` (from anything else this run): set `closed` to today's ISO date (date, not full timestamp — humans read this).
   - Flipping away from `complete` (regression): set `closed: null`.
   - No flip: leave `closed` as-is.
9. **Write the updated frontmatter back to `intent.md`.** Frontmatter only — never touch the body (everything after the closing `---` is read-only here). Preserve key order, YAML formatting, and **any unrecognized keys** — other skills or future versions may add fields not enumerated in step 7's contract; leave them untouched rather than silently dropping them. **Skip the writeback entirely if no field would change.** Specifically: if the freshly-derived `status`, `closed`, `verdict_outcomes_passed`, `verdict_outcomes_passed_by_test`, and `verdict_outcomes_total` all match the existing values, do NOT update `verdict_checked_at` and do NOT rewrite the file. This prevents constant git churn from `/spec-check` runs that found no semantic change.

## Constitution-drift section

Run **once per spec-check invocation** (not per intent). For each principle, ask: does any part of the current code or any current EARS outcome (across all checked intents) violate this principle? Grep for the principle's keywords (e.g., a "static typing" principle ⇒ look for untyped surfaces). Classify each principle as `pass`, `fail`, or `not applicable to this scope`.

## Report format

Print one combined report to stdout. Do NOT write the report to a file — drift reports are ephemeral and tied to a specific moment in time.

```markdown
# spec-check report — YYYY-MM-DD

## I-1: <title>  [status: in_progress, 3/5 outcomes passing, 1/5 by test]

### Code drift
- [x] O-1: <EARS text> — pass (test). `pytest tests/test_foo.py::test_bar` exit 0 in 0.42s.
- [ ] O-2: <EARS text> — fail (test). `pytest tests/test_foo.py::test_baz` exit 1 in 0.18s. Tail:
      ```
      E       assert latency_ms < 200
      E       AssertionError: 247 not < 200
      ```
- [x] O-3: <EARS text> — pass (agent). prompt: specs/INTENT/I-1-toggle/checks/error_copy_tone.md.
      Reason: copy in src/ui/error.tsx:42 is concise and actionable.
      Cited: src/ui/error.tsx:42, src/ui/error.tsx:51.
- [ ] O-4: <EARS text> — fail (agent). prompt: specs/INTENT/I-1-toggle/checks/help_text_wording.md.
      Reason: help text omits the keyboard shortcut required by the SHALL.
      Cited: src/ui/help.tsx:12.
- [?] O-5: <EARS text> — unverifiable (no test citation).
      Flag: add a [test: ...] citation via /spec-intent refine.

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
Across all intents: <N pass> (<X by test>), <F fail>, <U unverifiable>, <D intent-ahead>.
Test-citation coverage: <P>/<T> outcomes have a [test: ...] marker (<pct>%).
Agent-runner usage: <A>/<T> outcomes cite agent: (<pct>%).

Next: /spec-intent refine I-1
```

The `Next:` line is **conditional** and follows the Handoff convention documented in `spec-init`. Emit it **only** when at least one outcome in the run was classified `unverifiable` for a reason that `/spec-intent refine` can fix (missing citation, vague EARS, unknown runner, whole-suite citation, constitution-forbidden runner, agent prompt empty, agent prompt path outside repo, malformed agent citation, agent reply malformed, agent invocation error). Pick the lowest-numbered affected `I-N` **from the intents in this run's scope** — if invoked with `--intent I-K`, the affected intent is always `I-K` (it is the only intent in scope), regardless of unverifiable outcomes that may exist in other intents from prior runs. **Do NOT** emit `Next:` for `unverifiable (agent skipped)`, `unverifiable (--no-tests)`, `fail` outcomes, `intent-ahead` drift, or constitution-principle failures — the first two are user-opted run-mode artifacts (the user passed the flag), and the rest resolve in code or via `/spec-constitution amend` — `spec-check` can't tell which; the user's judgment owns the next move. When the run is clean (zero fail, zero unverifiable), omit `Next:` entirely — silence is the terminal signal.

The bracketed status header per intent shows the **newly derived** status, the overall verdict ratio (`_passed`/`_total`), and the test-backed ratio (`_passed_by_test`/`_total`). The test-backed ratio is the strongest signal and the one to push toward 100%.

Each outcome line MUST mark its verdict source explicitly: `pass (test)`, `pass (agent)`, `fail (test)`, `fail (agent)`, `unverifiable (no test citation)`, `unverifiable (agent skipped)`, `unverifiable (--no-tests)`, or `unverifiable (<other reason>)`. A reader scanning the report should never wonder whether a verdict came from a deterministic test, from an LLM-graded check, or from no check at all.

Agent-backed verdicts MUST surface the subagent's `reason:` line and its `cited:` paths in the report, indented under the verdict line. The subagent reply itself is **not persisted** — no log file is written. The report is the only place this evidence is presented; users who need the full transcript should re-run spec-check.

## Test Execution Rules

- **Citations are run in order**, not parallelized. Per-intent process-runner cost is bounded by the sum of timeouts (60s default per test), so a 5-outcome intent caps at 5 minutes worst-case for process runners. Users who need faster runs should narrow with `--intent I-N` rather than parallelizing — parallel test execution introduces ordering bugs that hide the very drift this skill is supposed to surface.
- **Each test runs in the repo root** (the same cwd `spec-check` was invoked in). If the project needs a different test cwd (monorepo subpackages, etc.), the citation MUST be a `shell:` runner that handles the `cd` itself. Do NOT auto-resolve cwd from the citation path — that's a guess, and guessing wrong silently passes the wrong test.
- **Environment is inherited.** spec-check does not strip env vars or activate virtualenvs. If a test needs a specific environment, set it before invoking `/spec-check`. The constitution is the right place to document required env (`Testing` bucket).
- **Test side effects are the user's problem.** The framework does NOT sandbox tests, mock the filesystem, or roll back DB writes. The constitution SHOULD carry a principle like "EARS-cited tests MUST be idempotent and side-effect-free" — `spec-intent` won't enforce that, but the user will feel the pain quickly if they violate it.
- **A flaky test is treated as `fail`, not `unverifiable`.** Exit codes are authoritative. If a test is flaky, the user must fix it or pin the seed — silently retrying would hide real regressions.
- **Agent runner timeout is 5 minutes**, not 60 seconds. Agent invocations are slower and more expensive than process tests; the longer timeout reflects that. Like the process-runner timeout, this is not user-configurable — citations that need longer should be split into multiple smaller checks. A timed-out agent classifies the outcome `unverifiable (agent timed out after 5 min)`, never `fail`.
- **Agent citations are not parallelized.** Same reasoning as the process runners — predictable ordering, no resource contention, no cost-spike on parallel subagent spawn. Per-intent worst case becomes `(process count × 60s) + (agent count × 300s)`; users who hit this should narrow with `--intent I-N`.
- **Agent runner respects the constitution whitelist** like every other runner. If the project's `specs/CONSTITUTION.md` declares e.g. `Testing: only pytest`, agent citations are classified `unverifiable (constitution forbids runner: agent)` — same code path as forbidding any other runner. No special case.
- **Agent runner respects `--no-agents` and `--no-tests`.** Both flags behave as documented in "Inputs"; `--no-agents` does not affect process runners.

## Agent Runner Mechanics

### Invocation tool

spec-check invokes the subagent via the Claude Code **`Agent` tool**, with `subagent_type: general-purpose`. The Agent tool is what unlocks the `agent` runner — without it in `allowed-tools`, the runner can't be invoked from inside the skill. The `general-purpose` subagent type is the right shape because the verifier needs read access to arbitrary files plus a working judgment loop; narrower subagent types like `Explore` are optimized for navigation reporting, which would bias the verdict toward "found stuff" rather than judging satisfaction of a SHALL.

The subagent is restricted to a read-only tool set via the invocation prompt: **`Read`, `Grep`, `Glob`, `WebFetch`** only. No Bash, no Edit, no nested Agent calls. The `WebFetch` grant exists so SHALLs that reference external resources ("the README MUST link to current API docs") can be verified — but the agent is instructed never to fetch unless the prompt file explicitly requires it.

### Prompt template

For each agent citation, spec-check builds the subagent's prompt by concatenating these segments in order:

Read [`AGENT_PROMPT.template.md`](AGENT_PROMPT.template.md) (sibling of this `SKILL.md`) for the prompt body. Substitutions: `<N>`, `<intent title>`, `<K>`, `<EARS line>`, `<cwd>`, `<path-1>`, `<free-text hint>`, `<prompt-file-path>`, `<prompt file contents>` are filled in by spec-check at invocation time. Keep the structure verbatim so the verdict parser below can find the `spec-check-verdict` fenced block.

### Verdict parser

After invocation, spec-check extracts the **last** `spec-check-verdict` fenced block from the reply, parses it as JSON, and validates against this schema:

1. The block exists. Missing → `unverifiable (agent reply malformed: no verdict block)`.
2. The body is valid JSON. Parse failure → `unverifiable (agent reply malformed: invalid JSON)`.
3. The object has exactly the keys `{verdict, reason, cited}`. Extra or missing → `unverifiable (agent reply malformed: key mismatch)`.
4. `verdict` is one of `"pass"`, `"fail"`, `"unverifiable"`. Otherwise → `unverifiable (agent reply malformed: bad verdict value)`.
5. `reason` is a non-empty string with no newlines (`\n` or `\r`). Otherwise → `unverifiable (agent reply malformed: bad reason)`.
6. `cited` is a JSON array of strings, each matching `^[^:]+:\d+$`, each resolving inside the repo (no `..` escape, no absolute outside cwd, no symlinks pointing outside). Otherwise → `unverifiable (agent reply malformed: cited entry not file:line)` or `unverifiable (agent reply malformed: cited path outside repo)`.
7. On `verdict = pass` or `fail`, `cited` MUST have 1–3 entries. Otherwise → `unverifiable (agent reply malformed: cited length must be 1..3 on pass/fail)`.
8. On `verdict = unverifiable`, `cited` MAY have 0–3 entries.

A malformed reply is **never retried** and is **never treated as `fail`** — a runner that couldn't return a clean verdict is not evidence the SHALL is broken. The exact malformed-reason string is surfaced in the report so the user can fix the prompt or re-author it.

### Timeout handling

- Per-citation cap: **5 minutes** (300 seconds). Hardcoded; not user-configurable. Rationale: agent calls are expensive, and a 5-minute ceiling matches the rough cost-per-check budget a small team can absorb on a pre-PR audit.
- On timeout, contribute `unverifiable (agent timed out after 5 min)` to the outcome's combined result. Never classify timeout as `fail`.
- Timeouts are not retried.

## Drift Classification Rules

- Be **specific**. Every `fail` MUST cite a file:line or an explicit "searched X, found nothing". Generic "this doesn't seem right" findings violate the EARS contract — the whole point of EARS is that drift maps to a precise SHALL.
- Be **honest about unverifiability**. If a SHALL is too vague to check (e.g., "THE SYSTEM SHALL feel responsive"), say so and recommend the user re-invoke `/spec-intent refine` to refine it.
- **Don't widen scope.** If the user asked for the toggle feature, don't audit the whole repo. Stay within the named scope unless the user opts in. Multi-intent runs are *by design* — they're not scope creep.
- **Don't fix.** This skill reports drift and writes the verdict frontmatter; it does not silently edit code, intent body content, or the constitution. Suggested remediations go in the report; applying them is the user's call.
- **Agent-backed fail MUST include the subagent's evidence.** A `fail (agent)` outcome MUST surface the subagent's `reason` (one line) and 1–3 file:line citations in the report. A fail with no agent evidence is a malformed reply — classify the outcome `unverifiable (agent reply malformed: missing evidence on fail)` instead. The whole point of citing a real test or a real prompt is that the verdict is grounded in artifacts.

## Edge Cases

- **No `specs/INTENT/` or empty directory** — refuse to run and tell the user to invoke `/spec-intent new` first.
- **No `specs/CONSTITUTION.md`** — proceed without the constitution-drift section, and note the omission in the report.
- **Intent has no `## Outcome` section or no EARS statements** — skip it in the multi-intent loop with NO frontmatter writeback (the intent's frontmatter, including `verdict_checked_at`, is left untouched). Continue with the other intents and name the skipped one in the report with a self-critique flag suggesting `/spec-intent refine`.
- **`--intent I-N` does not exist** — refuse, list existing IDs and statuses.
- **Malformed YAML frontmatter or missing `---` delimiters** — skip that intent in the multi-intent loop with NO writeback, note the parse error in the report, and suggest `/spec-intent refine` (or manual repair). Never partial-write a file whose frontmatter couldn't be parsed.
- **Legacy intent.md without a `status:` field** (e.g., a hand-created or pre-refactor file) — treat as if `status: draft`, run the full check, and produce a normal writeback (which will add the missing field). Do NOT crash. Other unrecognized legacy keys are preserved verbatim per step 9.
- **No code yet (greenfield)** — every cited `O-N` becomes `fail`. For process-runner outcomes the reason is `test not found at <path>`; for agent outcomes the reason is `agent prompt not found at <path>`. Outcomes with no citation are `unverifiable (no test citation)`, not `fail` — Path B is gone, so the absence of any citation can't produce a verdict at all. Status stays `draft`. That's a valid pre-implementation snapshot, not an error — the test paths and prompt paths in the citations double as a to-do list for the implementation.
- **Agent prompt file missing** — classify `fail (agent prompt not found at <path>)`. Greenfield signal, parallel to "test not found".
- **Agent prompt file empty** (zero bytes or whitespace-only) — classify `unverifiable (agent prompt empty at <path>)`. An empty prompt would force the subagent to invent the check, which would silently degrade to vibe-grading. Refuse it.
- **Agent prompt path outside the repo** (absolute path, `../` escape, or symlink target outside repo) — classify `unverifiable (agent prompt path outside repo: <path>)`. The convention is `specs/INTENT/I-N-<slug>/checks/<name>.md`; the prompt MUST live in the spec tree so it travels with the spec under version control.
- **Agent citation with shell metacharacters in the target** — classify `unverifiable (malformed agent citation: <target>)`. The agent runner takes a path, not a shell command; this prevents confusion with the `shell:` runner.
- **Agent subagent returns malformed verdict** — classify `unverifiable (agent reply malformed: <details>)`. Never silently retry; never silently treat as `fail`.
- **Agent subagent times out** (5-minute cap) — classify `unverifiable (agent timed out after 5 min)`. Same family as "test execution error".
- **Agent subagent invocation fails** (spawn error before the agent ran at all) — classify `unverifiable (agent invocation error: <message>)`.
- **Same prompt file cited by multiple outcomes in the same intent** — allowed. Each citation spawns its own subagent invocation; prompts may be reused across outcomes when the same check applies. Do NOT cache or dedupe — caching introduces ordering bugs that mask drift.

## What This Skill MUST NOT Do

- NEVER edit body content of `intent.md` — frontmatter writeback only.
- NEVER edit code or the constitution.
- NEVER report drift without a specific citation (file:line, commit SHA, runner+target+exit-code, or "searched X, found nothing").
- NEVER summarize multiple SHALLs into a single overall pass/fail — every EARS statement gets its own line.
- NEVER widen scope beyond what the user asked for (free-text scope hint).
- NEVER auto-flip a `superseded` intent's status — that field is set by `/spec-intent supersede` and is terminal.
- NEVER silently fall back from one runner to another. If a citation can't be parsed, can't be executed, or names a forbidden runner, classify the outcome `unverifiable` with the precise reason — do NOT pretend a different runner was the plan.
- NEVER inline an agent prompt in the report, in `intent.md`, or anywhere outside the prompt file itself. Agent prompts live in their own files; citations carry only the path.
- NEVER persist the subagent's reply to disk. The `reason` and `cited` lines are surfaced in the stdout report; nothing is written to a log file or a per-intent ledger.
- NEVER retry a failing test to chase flakiness. Exit codes are authoritative; flakiness is a user-fixable bug.
