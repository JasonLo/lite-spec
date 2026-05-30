# lite-spec

> **Status:** experimental — interfaces may change before v1.

A toolkit of five Claude Code skills (the `spec-` family) for the AI-era spec workflow. Enough structure for a solo developer or small team to think clearly and capture decisions, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

## Quickstart

Requires [Claude Code](https://claude.com/claude-code). Skills are modular agent capabilities Claude Code loads from `./.claude/skills/` (per-project) or `~/.claude/skills/` (global).

### Install the skills

Pick one route. Both pull from the same repo.

**Plugin marketplace** (Claude Code v2.1+) — installs into Claude Code's plugin cache, supports `/plugin update`, namespaces skills as `/lite-spec:spec-*`:

```claude
/plugin marketplace add JasonLo/lite-spec
/plugin install lite-spec@lite-spec
```

**Curl installer** — copies skill folders into `./.claude/skills/` (per-project) or `~/.claude/skills/` (global), keeps bare skill names (`/spec-init`, `/spec-intent`, …):

```bash
curl -LsSf https://raw.githubusercontent.com/JasonLo/lite-spec/main/scripts/install.sh | sh
```

The two routes differ only in slash-command naming; natural-language triggers ("set up lite-spec", "check for drift", etc.) work either way. The rest of this README uses the bare names — prefix with `lite-spec:` if you installed via the plugin route.

### Bootstrap the repo

```claude
/spec-init
```

Creates `specs/` and wires the `CLAUDE.md` pointer block so future Claude sessions know which spec files are human-owned vs. agent-writable.

### Basic flow

1. `/spec-constitution             # once: ratify project principles (amend later as needed)`
1. `/spec-intent new "<title>"     # open a new intent: problem, EARS outcomes, non-goals`
1. `... plan (optional) ...        # /spec-intent offers to hand the intent to /plan`
1. `... write code ...`
1. `/spec-decisions                # log non-trivial choices (or let Claude append directly)`
1. `/spec-check                    # verify code still satisfies open intents + constitution`

Each `/spec-intent new` creates `specs/INTENT/I-N-<slug>/intent.md` (the `experiments/` and `checks/` subfolders are added only when something needs them). After writing the intent, `/spec-intent` (in any of `new`/`refine`/`supersede`) offers to hand it to `/plan`; on yes, the resulting implementation plan is written to `specs/INTENT/I-N-<slug>/plan.md` — an agent-writable, regenerable sibling. Multiple intents may be open at once; `/spec-check` iterates every non-terminal intent and derives each one's `status` from outcome pass-counts.

### Writing outcomes: EARS in 60 seconds

`/spec-intent` asks you to phrase each success criterion as an **EARS** statement:

> **WHEN** `<trigger>` **THE SYSTEM SHALL** `<response>`.

- **trigger** — an observable event, state, or input ("when a client exceeds 5 attempts").
- **response** — externally observable behavior with a concrete threshold ("respond 429"), not "should feel fast".

Two other forms count too: `IF <condition> THEN THE SYSTEM SHALL <response>` for invariants, and `WHILE <state> THE SYSTEM SHALL <response>` for continuous behavior. One outcome per line. That's the whole notation — the structure is what lets `/spec-check` grade each `SHALL` individually instead of vibe-checking the feature as a whole.

### The lite path: test citations are opt-in

Each outcome *may* carry a `[test: ...]` citation so `/spec-check` can grade it mechanically (see [Test-backed verdicts](#test-backed-verdicts)). **You don't have to.** An intent with no citations simply rests at `status: draft` — a living spec you and Claude read for context, not a graded one. That's a valid resting state, not an error: `/spec-check` reports the outcomes as `unverifiable` and stops, with a one-line note (no nagging). Add citations when you want the status to *mean something* ("the code provably still does this"); skip them when you just want to capture intent. The `draft → in_progress → complete` ladder only starts climbing once at least one outcome is citable.

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`spec-init`](skills/spec-init/SKILL.md) | `specs/` + `specs/INTENT/` scaffold + `CLAUDE.md` pointers | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`spec-constitution`](skills/spec-constitution/SKILL.md) | `specs/CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. In ratify mode, surveys the codebase first to propose candidate principles from observed conventions (test runner, linter, package manager, etc.). |
| [`spec-intent`](skills/spec-intent/SKILL.md) | `specs/INTENT/I-N-<slug>/intent.md` | When opening, refining, or superseding an intent. Each intent is its own folder with EARS outcomes; `experiments/` and `checks/` subfolders appear only on demand. Frontmatter `status` is derived by `spec-check`. |
| [`spec-decisions`](skills/spec-decisions/SKILL.md) | `specs/DECISIONS.md` | When you make a non-trivial choice. Appends a one-line entry with rationale and an `[intent: I-N]` tag; supports supersession. Agent-writable. |
| [`spec-check`](skills/spec-check/SKILL.md) | drift report (stdout) + `intent.md` frontmatter writeback | Manual or auto-invoked — after edits to any `intent.md` or `CONSTITUTION.md`, as a pre-PR audit, or on phrases like "check for drift" / "verify against spec". Iterates every open intent; writes `status`, `verdict_*`, and `closed` back to each `intent.md`. |

> **`/plan` is not part of lite-spec.** It's Claude Code's built-in planning skill. `/spec-intent` *offers* to hand a freshly-written intent to `/plan` — which drafts a regenerable `plan.md` beside `intent.md` — but the handoff is opt-in. Say no and nothing external is needed; the five `spec-*` skills above are the whole toolkit. `intent.md` always stays the source of truth, `plan.md` is a working doc.

## How it fits together

Plain Markdown, no external services. `CONSTITUTION.md` and the `INTENT/` tree are human-owned (skill-guided); `DECISIONS.md` is agent-writable. EARS outcomes (`WHEN <trigger> THE SYSTEM SHALL <response>`) let `spec-check` grade each SHALL against code and derive each intent's `status`. Decisions carry an `[intent: I-N]` tag linking them back.

## A worked example

A short end-to-end run on a small Python project, showing the loop the linear flow above hides: **intent → code → check → refine → check**, with the verdict ratio climbing each pass.

**1. Bootstrap and ratify.**

```claude
/spec-init
/spec-constitution
```

`spec-constitution` surveys the repo, finds `pyproject.toml` + `uv.lock` + a `conftest.py`, and proposes principles you accept:

```markdown
## Code quality
- **P-1:** Code SHALL pass ruff with no warnings.
## Testing
- **P-2:** pytest SHALL be an allowed test runner for [test: ...] citations.
```

**2. Open an intent.**

```claude
/spec-intent new "rate-limit the login endpoint"
```

After eliciting, `spec-intent` writes `specs/INTENT/I-1-rate-limit-the-login-endpoint/intent.md`:

```markdown
---
id: I-1
status: draft
verdict_outcomes_passed: null
verdict_outcomes_total: null
---
## Outcome
- **WHEN** a client exceeds 5 login attempts in 60s **THE SYSTEM SHALL** respond 429. [test: pytest:tests/test_login.py::test_rate_limit]
- **WHEN** the window resets **THE SYSTEM SHALL** allow the next attempt. [test: pytest:tests/test_login.py::test_window_reset]
```

It then auto-runs `spec-check`. No code exists yet, so both cited tests are missing:

```
## I-1: rate-limit the login endpoint  [status: draft, 0/2 outcomes passing, 0/2 by test]
- [ ] O-1: ... — fail (test not found at tests/test_login.py).
- [ ] O-2: ... — fail (test not found at tests/test_login.py).
```

That `fail` list **is your to-do list** — the citations name the tests to write.

**3. Write the code and a test, then check.**

```claude
/spec-check --intent I-1
```

You implemented the limiter and `test_rate_limit`, but not `test_window_reset` yet:

```
## I-1: rate-limit the login endpoint  [status: in_progress, 1/2 outcomes passing, 1/2 by test]
- [x] O-1: ... — pass (test). pytest ... exit 0 in 0.3s.
- [ ] O-2: ... — fail (test not found at tests/test_login.py).
```

Status flipped `draft → in_progress` on its own. Log the design choice you made along the way:

```claude
/spec-decisions   # "sliding window, because fixed windows allow 2x bursts at the boundary"
```

→ `- **D-1:** Chose sliding-window rate limiting because fixed windows allow 2x bursts at the boundary (2026-05-30). [intent: I-1]`

(Had there been no open intent — say you were recording a repo-wide call like "adopt Postgres" — the entry would be tagged `[intent: none]` instead, no open intent required.)

**4. Finish and confirm.** Write the second test, run `/spec-check` once more, and the last outcome flips:

```
## I-1: rate-limit the login endpoint  [status: complete, 2/2 outcomes passing, 2/2 by test]
Status changes this run: I-1 in_progress → complete (closed 2026-05-30).
```

You never typed `status: complete` — `spec-check` derived it from the outcomes passing. And if you'd skipped the `[test: ...]` citations entirely, I-1 would have rested at `draft` with both outcomes `unverifiable` — the [lite path](#the-lite-path-test-citations-are-opt-in): still a useful spec, just not a graded one.

## Test-backed verdicts

Each EARS outcome may carry a `[test: <runner>:<target>]` citation. When present, `spec-check` runs the citation and uses the result — not an LLM grep — to decide pass vs. fail. Two flavors of runner exist:

**Process runners** (`pytest`, `vitest`, `jest`, `cargo`, `go`, `npm`, `shell`) — invoked via Bash; exit code 0 is the only path to a test-backed pass.

```markdown
- **WHEN** user submits the form **THE SYSTEM SHALL** show a toast within 200ms. [test: pytest:tests/test_form.py::test_toast_latency]
```

**Agent runner** (`agent:<path-to-prompt-file>`) — for SHALLs that can't be expressed as a deterministic test (UX copy tone, doc structure, narrative consistency). `spec-check` spawns a subagent against the prompt file plus the EARS line, the subagent emits a structured `pass`/`fail`/`unverifiable` verdict with file:line evidence, and the verdict + reason + citations are surfaced in the drift report.

```markdown
- **WHEN** an error blocks the user **THE SYSTEM SHALL** show concise, actionable copy. [test: agent:specs/INTENT/I-3-onboarding/checks/error_copy_tone.md]
```

The prompt file (`specs/INTENT/I-3-onboarding/checks/error_copy_tone.md`) is seeded with the SHALL by `/spec-intent` on first cite; the user enriches its `## Success criteria` section with concrete pass conditions.

`spec-check` writes two ratios back to the intent's frontmatter, forming a strength ladder:

- `verdict_outcomes_passed/_total` — overall passes.
- `verdict_outcomes_passed_by_test/_total` — passes verified by a process-runner test (strictest signal).

Invariant: `_passed_by_test ≤ _passed ≤ _total`. Outcomes without any `[test: ...]` citation are classified `unverifiable` — there is no grep + LLM fallback. The goal is to drive `_passed_by_test/_total` toward 1.0 over time, falling back to the `agent:` runner only when a SHALL is genuinely unprogrammable.

## Evaluating changes to the skills

`evals/` holds an A/B evaluation harness for measuring whether a change to the `spec-` skills actually improves outcomes. Given two git refs (variant A and variant B), it runs each against a fixed task set and produces a deterministic accept/reject/inconclusive verdict from four evidence streams — deterministic spec-adherence, an LLM-as-judge pairwise rubric, process/cost metrics, and a constitution hard-veto. A `--mock-carrier` mode exercises the full pipeline without API spend or Docker; the real carrier drives `claude` per variant. See [`evals/README.md`](evals/README.md) for usage.
