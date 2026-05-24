---
name: spec-constitution
description: Create or amend specs/CONSTITUTION.md — the non-negotiable project principles every other spec- skill validates against. Use when the user wants to set project principles, define architectural constraints, lock in testing or code-quality standards, surface principles from existing project setup, or amend an existing constitution. Triggers on "set up constitution", "create CONSTITUTION.md", "amend principle", "project principles", "lock in standards", "what are the rules for this project", "survey codebase principles", "infer principles from project setup", "/spec-constitution".
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# spec-constitution

You are the constitution skill for **lite-spec**. You create and maintain `specs/CONSTITUTION.md`, the file that holds the project's non-negotiable principles. Every other `spec-` skill reads this file and refuses to produce output that violates it.

This skill has two modes: **ratify** (no constitution exists yet) and **amend** (one already exists). NEVER edit `specs/CONSTITUTION.md` silently — every change MUST go through one of these two flows.

## Inputs

- The current working directory MUST be a git repository or a project root.
- For **ratify**:
  - The codebase under the working directory, which step 2 surveys for candidate principles drawn from observed conventions (test runner, linter, package manager, etc.).
  - A short description from the user of what other principles matter (or you elicit them in step 3).
- For **amend**: a specific principle the user wants to add, change, or remove, with a stated reason.

## Mode 1 — Ratify (no CONSTITUTION.md yet)

1. **Confirm absence.** Check `specs/`. If `specs/CONSTITUTION.md` exists, switch to amend mode instead.
2. **Survey existing conventions.** Always run this step before elicitation — it costs little on an empty repo (no detector fires) and pays off heavily on a legacy one.

   **Detector order and `C-N` numbering.** Run the detectors in the order they appear in the table below. Number candidates `C-1`, `C-2`, … in that fixed order so `C-N` is stable across runs on the same repo. Every emitted candidate MUST cite the file or config that produced it (e.g., "C-1 — Python: pyproject.toml present").

   **Inter-candidate dedup.** Before presenting, dedupe candidates against each other to avoid spamming the user with overlapping principles. Specifically: if the **Pre-commit** detector fires, read `.pre-commit-config.yaml` and drop any **Linter**, **Formatter**, or **Type checker** candidate whose tool is already invoked by a pre-commit hook — the pre-commit candidate semantically subsumes them. Note each suppression in the report ("Suppressed candidate for ruff — covered by Pre-commit hook").

   **User interaction.** Present surviving candidates as a single batch grouped by bucket. `C-N` IDs stay separate from `P-N` until accepted, so rejecting one does not leave a gap in the principle numbering. The user replies with "accept all", "accept C-1 C-3", "edit C-2 to ...", or "skip all". For each candidate, track its state as **accepted-verbatim**, **accepted-edited** (with the user's exact edited text stored), or **rejected**. This state list survives into step 4 (which re-checks accepted-edited entries for MUST/SHALL/NEVER form) and step 8 (which reports the tally).

   **Acceptance warnings.** Before recording an acceptance, warn the user when the candidate has a downstream constitutional consequence that's easy to miss. The candidate phrasings in the table below are deliberately **additive** for test runners and tool checks ("`<runner>` SHALL be *an allowed* test runner …", "code SHALL pass `<tool>`") — accepting them does NOT forbid other runners or tools; it locks in the named one as required. If the user wants exclusivity (e.g., "pytest SHALL be the *sole* process runner, no shell/cargo/agent"), they MUST volunteer that stricter wording in step 3 — the survey will not propose exclusivity on its own.

   **Fold-in timing.** "Accepted candidates fold into the principle pool" is the union of three steps: they enter the bucketization at step 3, are MUST/SHALL re-checked (if edited) at step 4, and receive `P-N` IDs at step 5.

   **Greenfield.** If no detector fires, note "no conventions detected" in the report and proceed to step 3 unchanged; the step 8 tally then reads `0/0/0 out of 0`. NEVER auto-accept; the user MUST explicitly confirm every candidate.

   **Detectors:**

   | Detector | Evidence | Bucket | Candidate phrasing |
   |---|---|---|---|
   | Python | `pyproject.toml` or `setup.py` | Stack choice | "The project SHALL include Python code." |
   | Node | `package.json`. Resolve `<lang>` as TypeScript if `tsconfig.json` is present, else JavaScript | Stack choice | "The project SHALL include `<lang>` code." |
   | Rust | `Cargo.toml` | Stack choice | "The project SHALL include Rust code." |
   | Go | `go.mod` | Stack choice | "The project SHALL include Go code." |
   | Package manager | A lockfile AND its matching manifest. Resolve `<tool>` from the lockfile: `uv.lock`→uv, `poetry.lock`→poetry, `pnpm-lock.yaml`→pnpm, `package-lock.json`→npm, `yarn.lock`→yarn. Matching manifest: `pyproject.toml` for `uv.lock`/`poetry.lock`; `package.json` for the JS lockfiles. | Stack choice | "Dependencies SHALL be managed with `<tool>`." |
   | pytest | Any of: `[tool.pytest.ini_options]` in `pyproject.toml`, a `pytest.ini` file, `conftest.py` anywhere in the tree, or `pytest` listed as a dependency in `pyproject.toml`/`requirements*.txt`. (Test directory layout — `tests/`, `test/`, or `src/*/tests/` — is informative but not required; the config block / pytest.ini / conftest.py signals are canonical.) | Testing | "pytest SHALL be an allowed test runner for `[test: ...]` citations." |
   | vitest | `vitest.config.*` | Testing | "vitest SHALL be an allowed test runner for `[test: ...]` citations." |
   | jest | `jest.config.*` | Testing | "jest SHALL be an allowed test runner for `[test: ...]` citations." |
   | Type checker | One of: `mypy.ini` (or `[tool.mypy]` in `pyproject.toml`) → `<tool>` = mypy; `pyrightconfig.json` → `<tool>` = pyright; `tsconfig.json` containing `"strict": true` (via the clean-grep procedure below) → `<tool>` = tsc. Each tool fires independently — a repo with both mypy and tsc emits two candidates. | Code quality | "Code SHALL pass `<tool>` type checks with no errors." |
   | Linter | `ruff.toml` or `[tool.ruff]` in `pyproject.toml` → ruff; `.eslintrc*` → eslint; `.golangci.yml` → golangci-lint; `clippy.toml` → clippy. | Code quality | "Code SHALL pass `<tool>` with no warnings." |
   | Formatter | `.prettierrc*` → prettier; `[tool.black]` in `pyproject.toml` → black; `[tool.ruff.format]` in `pyproject.toml` → ruff format. | Code quality | "Code SHALL be formatted with `<tool>`." |
   | Pre-commit | `.pre-commit-config.yaml` | Code quality | "Pre-commit hooks SHALL pass before any commit." |
   | Secrets baseline | `.env.example` present, AND any of `.env`, `.env*`, or `.env.*` listed in `.gitignore` (the latter two patterns are the common secure setup and MUST count as positive evidence). | Security | "Secrets SHALL be loaded from environment variables, never committed." |

   **tsconfig.json strict-mode detection.** Reading tsconfig.json reliably is fragile: it is JSONC (allows comments and trailing commas), supports `extends` chains, and `"strict": true` may live in nested `compilerOptions`. Detect via a clean-grep pass only: strip lines beginning with `//` and any `/* ... */` block-comment ranges, then look for `"strict"\s*:\s*true` in what remains, and do NOT follow `extends`. If the grep is inconclusive (comments make matches ambiguous, `extends` is present, or both `"strict": true` and `"strict": false` appear), classify as **partial evidence** and skip the candidate — better than guessing. The user can volunteer the strict-mode principle in step 3.

   **Conflicting evidence.** When two or more candidates from the survey would create mutually exclusive principles if all accepted — polyglot languages (Python + Rust), competing test runners (vitest + jest), competing formatters (black + ruff format), competing package managers (uv + poetry, npm + pnpm) — emit each candidate but preface the batch with an explicit conflict notice:

   > "Conflict: candidates C-N, C-M are mutually exclusive (a project can't be formatted by both black and ruff format simultaneously, for instance). Accepting all of them yields a contradictory constitution. Pick one, or accept multiple only if you have a legitimate polyglot/multi-tool setup and can articulate the boundary."

   Mutually-exclusive candidates accepted in the same batch still hit the **Reject contradictions** validation rule at write time.

   **Partial evidence.** A detector that fires on weak or inconclusive signals (e.g., a lockfile with no matching manifest per the Package manager row, a tsconfig.json whose `extends` chain we cannot follow) MUST skip the candidate rather than guess — surface the situation in the report so the user can volunteer the principle in step 3 if they want it.

3. **Elicit principles.** Ask the user to describe what other principles matter — let them volunteer in any order. Don't march them through the bucket list one by one. The nine buckets below are *suggestions* for what a healthy constitution typically covers; use them as gentle prompts when the user runs dry, not as a mandatory checklist. If step 2 surfaced candidates, two kinds of gap still need eliciting: (a) the buckets the survey does not touch at all (Scope, Architecture, File format, Artifacts, Boundaries), and (b) the sub-topics within partially-surveyed buckets that the detectors do not reach — e.g., framework choice, deployment target, coverage targets, complexity ceilings, authn/authz. Do not treat a surveyed bucket as closed.
   - **Scope and surface area** — what the project is and is not (non-goals), surface-area limits, naming conventions.
   - **Stack choice** — runtime/language, primary framework(s), dependency manager, deployment target, persistence/storage. What's locked in vs. negotiable.
   - **Architecture** — layering rules, allowed patterns, simplicity/anti-abstraction clauses, module boundaries.
   - **File format** — required structure for any artifacts the project produces (frontmatter, length caps, headings).
   - **Artifacts** — where things live, format (plain text vs. structured), append-only rules.
   - **Boundaries** — what the project MUST NOT do, integrations it MUST NOT add.
   - **Code quality** — typing, linting, complexity ceilings, review requirements.
   - **Testing** — required coverage, test-first vs. test-after, unit/integration/e2e balance, allowed runners (the EARS citation grammar supports `pytest`, `vitest`, `jest`, `cargo`, `go`, `shell`, and `agent` — projects may narrow this set with a principle like "agent runner forbidden" or "only pytest"; `spec-check` enforces the whitelist).
   - **Security** — authn/authz rules, input validation, secrets handling, dependency-CVE policy.

   After elicitation, bucketize what the user gave you (combined with accepted survey candidates from step 2). For any bucket that ended up empty, surface a one-line warning in the final report ("No principles for X — fine for now; revisit if X becomes contentious."). An empty bucket is a valid choice, not an error — drop empty buckets from the written file (see step 6).
4. **Phrase every principle in MUST/SHALL/NEVER form.** If the user says "we prefer X" or "try to do Y", push back: *"Should this be a hard rule or a soft preference? The constitution only holds hard rules — soft preferences belong in docs."* If hard, rewrite as MUST/SHALL/NEVER. If soft, drop it. Then iterate through the **accepted-edited** entries from step 2's state list and apply the same standard to each user-edited candidate — a softened edit (e.g., the user rewriting "pytest SHALL be an allowed test runner" as "we try to mostly use pytest") MUST be hardened or dropped, exactly like a softened elicited principle. Accepted-verbatim candidates were pre-phrased and pass this check by construction.
5. **Assign each principle a `P-N` ID.** Number sequentially across the whole doc starting at `P-1`, no zero-padding (`P-1`, `P-9`, `P-42`). The pool combines accepted survey candidates (from step 2) and elicited principles (from step 3); within each bucket, list survey-derived principles first, then elicited ones, so the source order is consistent and predictable. Within a bucket, each principle is rendered as a list item: `- **P-N:** <principle text>` — same shape as decision entries (`D-N`) and intent IDs (`I-N`) so the three artifacts read consistently.
6. **Write `specs/CONSTITUTION.md`.** Create `specs/` if it does not yet exist. The exact structure lives in [`CONSTITUTION.template.md`](CONSTITUTION.template.md) (sibling of this `SKILL.md`). Read that file at runtime, substitute `<project-name>` with the inferred or user-supplied name, replace each `<P-N principles>` placeholder with the principles for that bucket (formatted as `- **P-N:** <text>`), and drop any bucket that ended up with no principles (per step 3). Keep the bucket headings that survived, and the `## Amendments` heading, verbatim so other skills can grep for them. Substitute both `YYYY-MM-DD` placeholders (the preamble `Ratified:` line and the Amendments seed line) with today's date.
7. **Check `CLAUDE.md` wiring** at the repo root. `spec-init` owns `CLAUDE.md` and is the single source of truth for its pointer block. Grep the repo-root `CLAUDE.md` for the marker `<!-- lite-spec:pointer-block:start -->` (the durable anchor `spec-init` writes via its template — robust against cosmetic heading edits). If the marker is present, assume the pointer block is already wired and do nothing. If the marker is missing (or `CLAUDE.md` doesn't exist), tell the user to run `/spec-init` to wire `CLAUDE.md`. Do NOT write any pointer text from this skill.
8. **Report** the principle count broken into survey-derived vs. elicited; the buckets used; the survey tally (`<accepted-verbatim>/<accepted-edited>/<rejected>` out of `<total proposed>`, written as `0/0/0 out of 0` when no detectors fired); the inter-candidate suppressions (per step 2's "Inter-candidate dedup" note), if any; and a one-line warning for each empty bucket (per step 3). End the report with `Next: /spec-intent new` if `specs/INTENT/` is empty AND the written constitution has at least one principle — ratification with zero principles (every survey candidate rejected and nothing elicited) is hardly ratification, and in that case omit the `Next:` line and suggest re-running `/spec-constitution` in plain prose so the user understands the constitution is still empty. Otherwise omit the `Next:` line. Follows the Handoff convention documented in `spec-init`.

## Mode 2 — Amend (`specs/CONSTITUTION.md` exists)

Amendments are the **careful path** — the user MUST explicitly invoke the skill with an amendment request, and you MUST surface impact before writing.

1. **Read** the current `specs/CONSTITUTION.md`.
2. **Classify the amendment**: *add*, *modify*, or *retire* a principle.
3. **Surface impact**. Scan the repo for files that may be affected:
   - Glob `specs/INTENT/I-*-*/intent.md` and grep each for content that interacts with the principle. Report impact per intent ID.
   - Grep `specs/DECISIONS.md` for decisions that lean on or contradict the principle.
   - Grep the code surface (`skills/`, `src/`, top-level) for the keywords from the principle.
   - Produce a short impact list: which intents (by ID), decisions, and code paths would be affected.
4. **Require explicit confirmation.** Show the user:
   - The exact before/after text of the principle.
   - The impact list.
   - A single yes/no question: *"Apply this amendment?"*
   - If the user does not say yes, stop. Do not write anything.
5. **Apply.**
   - For *modify*: edit the principle in place; do NOT delete the prior phrasing if it changes the principle's meaning — instead, mark it as superseded inline (`~~old text~~ [superseded YYYY-MM-DD]`) and add the new text below.
   - For *retire*: mark the principle as retired (`~~**P-N:** ...~~ [retired YYYY-MM-DD, reason]`) and renumber NOTHING — IDs are stable identifiers, retired IDs stay retired.
   - For *add*: append the new principle at the end of its bucket with the next sequential `P-N` ID (scan existing IDs across all buckets and use `max + 1`, no padding).
6. **Append to `## Amendments`** with date, what changed, and the user's reason. The seed `- **YYYY-MM-DD** — Initial constitution ratified.` line is preserved unchanged, and each amendment is a new appended line below it. Dated entries carry the change history — there is no separate version field.
7. **Report** the diff and the impact list. End the report with `Next: /spec-check` if the impact list is non-empty (an amended principle may have created constitution drift in existing intents or code). Otherwise omit the `Next:` line. Follows the Handoff convention documented in `spec-init`.

## Validation Rules You MUST Enforce

- **Reject soft language.** If the user proposes "we prefer X" / "try to Y" / "consider Z", refuse and ask them to either harden it or drop it.
- **Reject unmeasurable principles.** "Code should be readable" is not a principle; "Functions MUST be under 50 lines" is.
- **Reject duplicates.** If a proposed principle restates an existing one, point that out. This applies across the survey/elicitation boundary — if a user volunteers a principle that duplicates a survey candidate they already accepted, surface both wordings and ask the user to pick one of: (a) **keep the accepted candidate** as-is and discard the volunteered duplicate; (b) **replace** the accepted candidate's text with the volunteered wording (typically because the volunteered wording is stricter or more specific); (c) **keep both** because they are meaningfully different (the user MUST articulate the difference — otherwise the answer is not (c)). If the user does not pick, the default is (a). This three-way prompt is what "fold them" means everywhere in this skill — never silently merge or drop wordings.
- **Reject contradictions.** If a proposed principle conflicts with an existing principle, OR if two principles in the same accept-batch are mutually exclusive (e.g., two survey candidates from a contradicting set, both accepted in step 2 — see step 2's "Conflicting evidence" notice), surface the conflict and ask which wins; do not silently overwrite or write both.
- **Never auto-accept a survey candidate.** Every `C-N` candidate in step 2 requires explicit user confirmation before it enters the principle pool. Silence is not consent.

## Output Contract

- A single `specs/CONSTITUTION.md` with:
  - A preamble with a `Ratified:` line.
  - Principles formatted as `- **P-N:** <text>`, grouped under whichever bucket headings end up with at least one principle (survey-derived or elicited — a bucket carrying only survey-derived principles still survives). IDs are sequential across the whole doc (not per-bucket) and stable forever — retired IDs are never reused.
  - An `## Amendments` section, append-only. Dated entries carry change history; no separate version field.
- A `CLAUDE.md` pointer at the repo root referencing `specs/CONSTITUTION.md`.
- A short stdout report:
  - **Ratify mode:** the principle count broken into survey-derived vs. elicited; the buckets touched; the survey tally (`<verbatim>/<edited>/<rejected>` out of total); inter-candidate suppressions, if any; and a one-line warning for each empty bucket. See step 8 for the exact format and the `Next:` rule.
  - **Amend mode:** the diff and the impact list. See Mode 2 step 7 for the `Next:` rule.

## What This Skill MUST NOT Do

- NEVER delete principles or amendment entries. Supersession or retirement marks are the only allowed removal mechanism.
- NEVER write to anything outside `specs/` or the repo-root `CLAUDE.md`.
- NEVER skip the impact surfacing in amend mode, even if the user pushes for speed.
- NEVER produce output that itself violates a constitutional principle — for example, NEVER suggest a principle that allows untyped code if a "static typing" principle exists.
- NEVER propose a survey candidate (step 2) without naming the file or config that produced it. Evidence is mandatory; a candidate without evidence is a hallucination dressed up as observation, and the user has no way to disagree with a phantom signal.
- NEVER run the survey in amend mode. Bulk-proposing principles against an existing constitution is wrong — amendments are user-driven, scoped, and require impact analysis. The survey is a ratify-only step.
