---
name: spec-intent
description: Draft, refine, or supersede an intent under specs/INTENT/I-N-<slug>/intent.md — a one-page doc with problem, outcome (in EARS notation), non-goals, constraints, and an append-only change log, plus frontmatter status managed by spec-check. Use when the user describes a new feature in loose terms, wants to capture intent before coding, asks for a spec, wants to refine an existing intent, or wants to retire an intent in favor of a successor. Triggers on "write an intent doc", "spec this feature", "capture intent", "new intent", "draft intent", "refine intent", "supersede intent", "what's the intent", "/spec-intent".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
---

# spec-intent

You are the intent skill for **lite-spec**. You create, refine, and supersede intent docs under `specs/INTENT/I-N-<slug>/intent.md` — one folder per intent, with `experiments/` nested inside it. Each intent doc captures **problem, outcome, non-goals, constraints, and change log**, with skill-managed frontmatter (`status`, `verdict_*`, `closed`) maintained by `spec-check`. Outcomes use EARS notation so drift can be checked mechanically.

This skill has three subcommands: **`new`**, **`refine`**, and **`supersede`**.

## Inputs

- The current working directory MUST be a project root and MUST contain `specs/INTENT/` (created by `/spec-init`). If it doesn't, refuse and tell the user to run `/spec-init`.
- For `new`: a loose feature description and a title.
- For `refine`: optionally `--intent I-N` to scope to one intent; otherwise the skill auto-resolves (single open intent ⇒ use it; zero or many ⇒ prompt).
- For `supersede`: `--intent I-N` (the intent being retired) and `--by-new "<title>"` (the successor's title).
- If `specs/CONSTITUTION.md` exists, you MUST read it and validate your output against it.

## Frontmatter contract

Every `intent.md` carries this frontmatter:

```yaml
---
id: I-<N>                   # immutable; monotonic integer, assigned at creation
title: <title>              # user-edited via /spec-intent refine
slug: <slug>                # immutable; derived from title at creation
status: draft               # SKILL-MANAGED by spec-check (draft|in_progress|complete|superseded)
opened: YYYY-MM-DD          # immutable; set at creation
closed: null                # SKILL-MANAGED by spec-check (set on flip to complete; cleared on regression)
superseded_by: null         # set by /spec-intent supersede (the only user-triggered frontmatter mutation)
verdict_outcomes_passed: null         # SKILL-MANAGED by spec-check
verdict_outcomes_passed_by_test: null # SKILL-MANAGED by spec-check (subset of _passed verified by a test, not just grep)
verdict_outcomes_total: null          # SKILL-MANAGED by spec-check
verdict_checked_at: null              # SKILL-MANAGED by spec-check
---
```

- **Skill-managed fields** (`status`, `closed`, `verdict_*` including `verdict_outcomes_passed_by_test`) are written by `spec-check`. Hand-edits to these will be overwritten on the next run.
- **`superseded_by`** is set only by `/spec-intent supersede`.
- **`title`** may be changed via `/spec-intent refine`. **`id`**, **`slug`**, and **`opened`** are immutable post-creation; the folder name `I-N-<slug>/` is also immutable (renaming breaks the `superseded_by` chain and `[intent: I-N]` references in `DECISIONS.md`).

## Subcommand 1 — `new "<title>"`

1. **Read the constitution.** If `specs/CONSTITUTION.md` exists, read it. Keep its principles in mind for every step. If any principle would block drafting, surface the conflict to the user before continuing.
2. **Assign the ID.** Glob `specs/INTENT/I-*-*/`. Extract the integer `N` from each folder name (strip the `I-` prefix and the trailing `-<slug>`); compute `N_new = max(N) + 1` (or `1` if no existing intents). Format as `I-<N>` with no zero-padding (`I-1`, `I-42`) — same shape as `D-N` decisions and `P-N` principles.
3. **Derive the slug.** Take the title, lowercase it, replace non-`[a-z0-9]` runs with single hyphens, strip leading/trailing hyphens. Then handle each edge case:
   - **Empty result** (title was all punctuation, all non-ASCII, or empty after normalization): refuse with an explanatory message and ask the user for an ASCII-sluggable title. Do NOT create the folder.
   - **Multi-token slug longer than 40 chars** (one or more hyphens, joined length >40): split on `-` and drop trailing tokens until the joined length is ≤40; strip any trailing hyphen artifact. Never split mid-word.
   - **Single-token slug longer than 40 chars** (no hyphens, length >40): truncate at 40 characters — a single token can't be word-split, and a 40-char folder name is better than rejecting the user's title.
   - **Otherwise**: use the slug as-is.
4. **Create the folder.** `mkdir -p specs/INTENT/I-<N_new>-<slug>/experiments/`. The `experiments/` subdir is created empty — it's the home for any experiment files that back this intent.
5. **Elicit the five sections.** Ask one focused question per section that's underspecified. Do NOT ask questions the user has already implicitly answered. Skip a section only if it genuinely doesn't apply.
   - **Problem** — what's broken or missing today, in 1–3 sentences. Push for a concrete *current-state* description, not aspirational language.
   - **Outcome** — what success looks like, framed as 1–5 EARS statements. (See "EARS rules" below.)
   - **Non-Goals** — what is explicitly out of scope. If the user can't name 3+, suggest some based on adjacent territory you'd expect them to skip.
   - **Constraints** — technical, organizational, or design constraints that bound the solution.
   - **Change Log** — seeded with `- **YYYY-MM-DD** — Initial draft.` (today's date).
6. **Write the EARS outcomes.** Every outcome statement MUST take the form `**WHEN** <trigger> **THE SYSTEM SHALL** <response>.` Reject vague responses. Examples:
   - Bad: `THE SYSTEM SHALL be fast.` → push the user for a number: `under 100ms`, `p99 < 250ms`, `single render frame`.
   - Bad: `THE SYSTEM SHALL handle errors gracefully.` → push for behavior: `display a retry banner and preserve form input`.
   - If the user resists giving a measurable threshold, write `THE SYSTEM SHALL <response> (threshold TBD)` and add a self-critique flag — do not silently let vagueness slide.

   **Then cite an executable test for each outcome.** Append a `[test: <runner>:<target>]` marker so `spec-check` can verify the SHALL mechanically. See "Test citations" below for the grammar. If the test doesn't exist yet (greenfield), still cite the path you intend to write — `spec-check` will classify it `fail (test not found)` until the file lands, which is the correct pre-implementation signal.

   **If the user can't name a process-runner test, offer the agent runner before falling to `unverifiable`.** Walk the user through: "Could a subagent verify this by reading specific files against a prompt? If yes, propose the prompt's filename (`specs/INTENT/I-<N_new>-<slug>/checks/<name>.md`) and a one-sentence summary of what it should check; the prompt file itself is seeded automatically with the SHALL and enriched by the user later." If the user agrees, cite `[test: agent:specs/INTENT/I-<N_new>-<slug>/checks/<name>.md]`. The agent runner is a strictly weaker signal than a process runner — only reach for it when the SHALL is genuinely unprogrammable (UX claims, doc structure, narrative consistency).

   If even the agent runner can't apply (the SHALL is truly subjective, like "users will love it"), omit the marker and flag in the self-critique pass that this outcome will be `unverifiable` at check time.
7. **Self-critique pass.** Before finalizing, run through the doc and flag, then fix, each of:
   - **Vague EARS responses** — any "fast", "easy", "robust", "graceful" without a measurable companion.
   - **Missing non-goals** — territory adjacent to the problem the user didn't exclude.
   - **Hidden assumptions** — claims that depend on something the user hasn't stated.
   - **Scope-creep risks** — outcomes that secretly require building a much larger system.
   - **Unstated dependencies** — external services, libraries, or upstream work the outcome silently requires.
   - **Missing test citation** — any EARS outcome without a `[test: <runner>:<target>]` marker. Flag it. Try the runners in this order before accepting `unverifiable`: process runner (pytest/vitest/jest/cargo/go/npm/shell) → agent runner → omit. The agent runner is allowed but is a weaker signal than any process runner; do not propose `agent:` when a process runner would work.
   - **Agent-runner misuse** — any outcome citing `agent:` where a process runner could express the same SHALL. The agent runner is for genuinely unprogrammable SHALLs (UX, doc structure, narrative consistency). If the SHALL has a measurable threshold ("under 200ms", "exit code 0", "contains X"), a process runner is correct and the agent citation is a smell — push back, propose a process-runner citation, and rewrite if the user agrees.
   - **Agent prompt file missing** — for each `[test: agent:<path>]` citation, check whether the prompt file exists. If not, note in the self-critique that the seed will be created at write time (step 10 below) but the user MUST enrich its `## Success criteria` section with concrete pass conditions before `/spec-check` can return a real verdict.
8. **Validate against the constitution.** Walk each principle and confirm the intent doesn't violate it. If a violation exists, refuse to finalize and tell the user which principle is blocking — they MUST either revise the intent or invoke `/spec-constitution` to amend the principle.
9. **Write `specs/INTENT/I-<N_new>-<slug>/intent.md`.** Read [`INTENT.template.md`](INTENT.template.md), substitute `<N>` → `N_new`, `<title>`, `<slug>`, `<user>` (from git config or env), `YYYY-MM-DD` → today, fill the section bodies with the elicited content, and write the result. Keep section headings verbatim so `spec-check` and other skills can grep for them. Initial frontmatter: `status: draft`, `opened: <today>`, all other skill-managed fields `null`.
10. **Seed agent prompt files** for every `[test: agent:<path>]` citation. For each citation whose target lives under `specs/INTENT/I-<N_new>-<slug>/checks/`, `mkdir -p` the parent directory and, **only if the prompt file does not yet exist**, create it pre-populated with the SHALL line under a `## SHALL` heading, like:

    ```markdown
    # Agent check: <one-line summary the user gave during elicitation>

    ## SHALL
    <verbatim EARS line, including the `[test: ...]` marker so the file is self-contained>

    ## Success criteria
    _Enrich this section with concrete pass conditions: what files to inspect, what patterns count as satisfaction, what file:line evidence the subagent should cite. The seeded SHALL alone is intentionally minimal — `spec-check` will run against whatever is here, so the more specific the better._
    ```

    Do NOT overwrite an existing prompt file — the user may have authored it separately. Do NOT author the Success criteria body content beyond the placeholder paragraph above; populating it is the user's responsibility (see "Agent prompt files are user-owned" under "What This Skill MUST NOT Do"). For agent citations that point **outside** the intent's local `checks/` directory (a centralized prompt at e.g. `specs/checks/<name>.md`), do NOT create the directory or seed the file — only the local `checks/` convention triggers seeding.
11. **Auto-trigger `spec-check --intent I-<N_new>`.** If `spec-check` is not installed, note that drift verification should be run manually once the implementation exists.
12. **Report** the path, the assigned ID, word count (target <300 words for the body), the number of EARS outcomes, and any self-critique flags that were left unresolved. Note that `spec-check` was auto-invoked and its report follows. **Do NOT emit a `Next:` line from `spec-intent` itself** — the auto-triggered `spec-check` run owns the handoff and ends with its own conditional `Next:` (see the Handoff convention in `spec-init`). On a fresh draft, expect `spec-check` to classify every cited test as `fail (test not found at <path>)` and emit no `Next:` line — that fail-heavy report is the intentional greenfield signal that implementation is the next step (code work doesn't get a `Next:` pointer per the convention). If `spec-check` is not installed, append a plain note that drift verification must be run manually once the implementation exists, and omit `Next:` entirely — never emit free text after the `Next:` token, since the convention requires `Next: /<skill> [args]` format.

## Subcommand 2 — `refine [--intent I-N]`

1. **Resolve the target intent.**
   - If `--intent I-N` is passed, use it. If no folder matches `specs/INTENT/I-N-*/`, refuse and list the existing IDs.
   - Otherwise, glob `specs/INTENT/I-*-*/intent.md` and read each frontmatter `status`. Collect those with `status` in `{draft, in_progress}` — the **open** intents.
     - Exactly one open intent ⇒ use it; report the choice in the run output.
     - Zero or many ⇒ prompt the user for `--intent I-N`, listing every intent ID and status (including terminal `complete` and `superseded` intents — refining a terminal intent to fix a typo or append a Change Log clarification is legal here, unlike in `spec-decisions` where new tags only auto-bind to open intents). Do NOT guess.
2. **Read** the intent.md and the constitution.
3. **Ask the user what's changing** — a clarification, a new outcome, a tightened non-goal, a removed constraint, a title update. Do not guess.
4. **Apply the change** in place to the body sections (Problem, Outcome, Non-Goals, Constraints, the `Last updated:` line, and optionally the `title:` frontmatter field). NEVER touch skill-managed frontmatter fields. NEVER delete or overwrite Change Log entries.
5. **Re-run the self-critique pass** on the affected sections.
6. **Validate against the constitution** again.
7. **Append a new Change Log entry** with today's date, what changed, and a one-sentence reason.
8. **Seed agent prompt files** for any newly-added `[test: agent:<path>]` citations whose target lives under `specs/INTENT/I-N-<slug>/checks/`. Apply the same logic as step 10 of `new`: `mkdir -p` the parent directory; create the file pre-populated with the SHALL line under `## SHALL` and a `## Success criteria` placeholder, **only if the file does not yet exist**. Never overwrite. Refines that only modify existing agent citations (e.g., changing the prompt path) do NOT delete the old seed file — that's the user's call.
9. **Auto-trigger `spec-check --intent I-N`.** A Change Log append means drift is possible; checking immediately is cheaper than discovering it later.
10. **Report** the diff and any self-critique flags. The auto-triggered `spec-check` report follows; let it own the `Next:` line per the Handoff convention in `spec-init`. Do NOT emit a `Next:` line from `spec-intent` itself. If `spec-check` is not installed, append a plain note that drift verification must be run manually, and omit `Next:` entirely — never emit free text after the `Next:` token.

## Subcommand 3 — `supersede --intent I-N --by-new "<title>"`

1. **Resolve `I-N`.** If `--intent` is missing, apply the same single-open-auto-pick rule as `refine`. If the resolved intent already has `status: superseded`, refuse — an intent can be superseded only once.
2. **Read the constitution.**
3. **Open the successor.** Run the full `new` subcommand pipeline (elicit, write EARS, self-critique, constitution check) to produce `specs/INTENT/I-<M>-<new-slug>/intent.md`, where `M = max(existing N) + 1`. Override the `new` pipeline's default Change Log seed with this single combined line (substitute today's date and the predecessor's ID):
   - `- **YYYY-MM-DD** — Initial draft. Supersedes I-<N>.`
4. **Update the predecessor `I-N/intent.md` frontmatter:**
   - `status: superseded`
   - `superseded_by: I-<M>`
   - `closed: <today>` if not already set
   - Append `- **YYYY-MM-DD** — Superseded by I-<M>.` to its Change Log. Body sections (Problem, Outcome, Non-Goals, Constraints) are left untouched — they remain as the historical record of what I-N tried to do.
5. **Auto-trigger `spec-check --intent I-<M>`** on the successor only — the predecessor is terminal and does not need re-checking. (`spec-check` will skip a `superseded` intent unless explicitly named.)
6. **Report** both IDs, the successor's path, and any self-critique flags from the new draft. The auto-triggered `spec-check` report follows; let it own the `Next:` line per the Handoff convention in `spec-init`. Do NOT emit a `Next:` line from `spec-intent` itself. If `spec-check` is not installed, append a plain note that drift verification must be run manually, and omit `Next:` entirely — never emit free text after the `Next:` token.

## EARS rules

- **Form:** `WHEN <trigger> THE SYSTEM SHALL <response>.` Both clauses are required.
- **Trigger** describes an observable event, state, or input — not an internal mood ("when the team feels strongly").
- **Response** describes externally observable behavior with a threshold or specific outcome — not "should work well".
- Use `IF ... THEN THE SYSTEM SHALL ...` for conditional invariants and `WHILE ... THE SYSTEM SHALL ...` for continuous behaviors. These are also valid EARS forms.
- One outcome per statement. If the response has an "and", consider splitting.

## Test citations

Each EARS outcome SHOULD carry one or more `[test: <runner>:<target>]` markers so `spec-check` can verify the SHALL by executing code or by spawning a subagent against a curated prompt — not by grep + LLM judgment (which no longer exists). The marker may appear inline at the end of the EARS line, or as indented sub-bullets directly under it (use sub-bullets when the line gets long or there are >1 tests):

```
- **WHEN** user submits the form **THE SYSTEM SHALL** show a toast within 200ms. [test: pytest:tests/test_form.py::test_toast_latency]

- **WHEN** input is invalid **THE SYSTEM SHALL** preserve form state and display a retry banner.
  - [test: vitest:src/form.test.ts -t "preserves state on invalid input"]
  - [test: vitest:src/form.test.ts -t "shows retry banner"]
```

**Allowed runners** (anything outside this list is rejected by `spec-check`):

| Runner | Citation | Command `spec-check` runs |
|---|---|---|
| `pytest` | `pytest:<test-id>` | `pytest -x <test-id>` |
| `vitest` | `vitest:<args>` | `npx vitest run <args>` |
| `jest` | `jest:<args>` | `npx jest <args>` |
| `cargo` | `cargo:<test-name>` | `cargo test <test-name>` |
| `go` | `go:<-run pattern> [pkg]` | `go test -run <pattern> <pkg or ./...>` |
| `npm` | `npm:<script-name>` | `npm run <script-name>` |
| `shell` | `shell:<command>` | the command verbatim (escape hatch — use sparingly) |
| `agent` | `agent:<path-to-prompt-file>` | spawns a subagent with the prompt file + EARS line + scope hints; structured verdict required |

The `shell:` runner is allowed but flagged in `spec-check` reports as a weaker signal than a structured runner, because it bypasses test-runner conventions (exit codes are still authoritative). Prefer a structured runner whenever possible.

The `agent:` runner is **the second-weakest signal** in the citation grammar — strictly weaker than any process runner. Prefer a process runner whenever the SHALL can be expressed as a deterministic test. Reach for `agent:` only when the SHALL is genuinely unprogrammable — a UX claim ("error copy MUST be concise and actionable"), a doc-structure invariant ("the README MUST mention installation before usage"), or a narrative-consistency check across files. The prompt MUST live in a file (`specs/INTENT/I-N-<slug>/checks/<name>.md` by convention) and MUST NOT be inlined into the citation. `spec-check` invokes a subagent against the prompt file and parses a structured verdict; cost and runtime are both higher than a process runner (5-minute per-check timeout vs. 60 seconds). `spec-intent` lazily creates the `checks/` directory and seeds the prompt file with the SHALL when a citation references a path inside the local intent folder — the user enriches the seeded `## Success criteria` section over time. Agent-backed passes count toward `_passed_by_agent` in the intent's frontmatter but never toward the strictest `_passed_by_test` ratio.

A test citation MUST point at a single test (or a tight `-k` / `-t` / `-run` filter). Whole-suite citations like `pytest:tests/` are rejected — one SHALL → one test (or a small named group), so a regression maps to a specific outcome. An `agent:` citation MUST point at a single prompt file, not a directory or a glob; multiple outcomes MAY reuse the same prompt file when the same check genuinely applies, but each cites it explicitly.

## What This Skill MUST NOT Do

- NEVER write outcomes in non-EARS prose.
- NEVER delete or rewrite past Change Log entries — they are append-only.
- NEVER touch skill-managed frontmatter fields (`status`, `closed`, `verdict_outcomes_passed`, `verdict_outcomes_passed_by_agent`, `verdict_outcomes_passed_by_test`, `verdict_outcomes_total`, `verdict_checked_at`) directly — only `spec-check` writes those. **Exception:** the `supersede` subcommand sets `status: superseded`, `superseded_by: I-<M>`, and `closed: <today>` on the predecessor (step 4 of subcommand 3). That is the one documented mutation of skill-managed fields by `spec-intent`; all other writes to these fields are forbidden.
- NEVER hand-edit `superseded_by` outside the `supersede` subcommand. The chain `I-N → superseded_by → I-M` is the durable handle that spec-check uses to skip terminal intents and that `[intent: I-N]` decision tags rely on. Breaking it silently invalidates downstream skills.
- NEVER rename an existing `I-N-<slug>/` folder. The folder name is the durable handle that `superseded_by` and `[intent: I-N]` references in `DECISIONS.md` rely on.
- NEVER finalize an intent that violates `specs/CONSTITUTION.md`. Surface the conflict instead.
- NEVER skip the self-critique pass — even on tiny refinements, walk the five flags.
- NEVER fabricate user answers. If a section is genuinely unknown, leave it as `TBD` with a self-critique flag rather than inventing detail.
- NEVER offer a `complete` subcommand — completion is *derived* by `spec-check` from outcome pass-counts, not declared by the user.
- NEVER inline an agent prompt body inside an `intent.md` outcome or sub-bullet. Prompts live in their own files under `specs/INTENT/I-N-<slug>/checks/`; citations carry only the path.
- NEVER propose an `agent:` citation when a process runner would express the same SHALL. The agent runner is a strictly weaker signal and should be reached for only when the SHALL is unprogrammable.
- NEVER author or rewrite the body of an existing prompt file. The skill creates the directory and seeds the file with the SHALL + a `## Success criteria` placeholder on first cite (step 10 of `new`, step 8 of `refine`); enriching `## Success criteria` and everything after is the user's responsibility. **Agent prompt files are user-owned.**
