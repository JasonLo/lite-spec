# lite-spec

> **Status:** experimental — interfaces may change before v1.

A toolkit of four Claude Code skills (the `spec-` family) for the AI-era spec workflow. Enough structure for a solo developer or small team to think clearly and capture intent, without the ceremony of GitHub Spec Kit, OpenSpec, or BMAD-METHOD.

## Mental model

Four artifacts, and one rule: you write intents, Claude writes code, `/spec-check` grades the code against each intent and **derives the status** — you never set it by hand.

| Artifact | What it holds | Who owns it |
|---|---|---|
| `specs/CONSTITUTION.md` | Project-wide principles every intent must respect (optional) | You — via `/spec-constitution` |
| `specs/INTENT/I-N-<slug>/intent.md` | One feature's problem + EARS outcomes | You — via `/spec-intent` |
| `specs/INTENT/I-N-<slug>/plan.md` | Optional, regenerable implementation plan | The agent — via `/plan` |
| `CLAUDE.md` pointer block | Wiring that tells Claude which files are which | `/spec-init` |

An intent climbs a status ladder as more of its EARS outcomes pass:

```text
draft → in_progress → complete     (drops back if a passing outcome later breaks;
                                    superseded = retired for a successor)
```

Everything else below is detail on those four files.

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

1. `/spec-intent new "<title>"     # open an intent: problem, EARS outcomes, non-goals`
1. `... plan (optional) ...        # /spec-intent offers to hand the intent to /plan`
1. `... write code ...`
1. `/spec-check                    # verify the code still satisfies your open intents`

Optional, once you have a couple of intents: `/spec-constitution` locks in project-wide rules (test runner, linter, architecture) that every intent is then checked against. Intents work fine without it — add it when you want the guardrails.

Each `/spec-intent new` creates `specs/INTENT/I-N-<slug>/intent.md` (the `experiments/` and `checks/` subfolders are added only when something needs them). After writing the intent, `/spec-intent` (in any of `new`/`refine`/`supersede`) offers to hand it to `/plan`; on yes, the resulting implementation plan is written to `specs/INTENT/I-N-<slug>/plan.md` — an agent-writable, regenerable sibling. Multiple intents may be open at once; `/spec-check` iterates every non-terminal intent and derives each one's `status` from outcome pass-counts.

### Writing outcomes: EARS in 60 seconds

`/spec-intent` asks you to phrase each success criterion as an **EARS** statement:

> **WHEN** `<trigger>` **THE SYSTEM SHALL** `<response>`.

- **trigger** — an observable event, state, or input ("when a client exceeds 5 attempts").
- **response** — externally observable behavior with a concrete threshold ("respond 429"), not "should feel fast".

Two other forms count too: `IF <condition> THEN THE SYSTEM SHALL <response>` for invariants, and `WHILE <state> THE SYSTEM SHALL <response>` for continuous behavior. One outcome per line. That's the whole notation — the structure is what lets `/spec-check` grade each `SHALL` individually instead of vibe-checking the feature as a whole.

### Context-only intents: test citations are opt-in

Each outcome *may* carry a `[test: ...]` citation so `/spec-check` can grade it mechanically (see [Test-backed verdicts](#test-backed-verdicts)). **You don't have to.** An intent with no citations is a *context-only intent* — it rests at `status: draft`, a living spec you and Claude read for context rather than one that's graded. That's a valid resting state, not an error: `/spec-check` reports the outcomes as `unverifiable` and stops, with a one-line note (no nagging). Add citations when you want the status to *mean something* ("the code provably still does this"); skip them when you just want to capture intent. The `draft → in_progress → complete` ladder only starts climbing once at least one outcome is citable.

## The skills

| Skill | Artifact | When to use |
|---|---|---|
| [`spec-init`](skills/spec-init/SKILL.md) | `specs/` + `specs/INTENT/` scaffold + `CLAUDE.md` pointers | Once per repo. Bootstraps a project to use lite-spec (or repairs a partial setup). |
| [`spec-constitution`](skills/spec-constitution/SKILL.md) | `specs/CONSTITUTION.md` | Once per project, plus amendments. Locks in non-negotiable principles every other skill validates against. In ratify mode, surveys the codebase first to propose candidate principles from observed conventions (test runner, linter, package manager, etc.). |
| [`spec-intent`](skills/spec-intent/SKILL.md) | `specs/INTENT/I-N-<slug>/intent.md` | When opening, refining, or superseding an intent. Each intent is its own folder with EARS outcomes; `experiments/` and `checks/` subfolders appear only on demand. Frontmatter `status` is derived by `spec-check`. |
| [`spec-check`](skills/spec-check/SKILL.md) | drift report (stdout) + `intent.md` frontmatter writeback | Manual or auto-invoked — after edits to any `intent.md` or `CONSTITUTION.md`, as a pre-PR audit, or on phrases like "check for drift" / "verify against spec". Iterates every open intent; writes `status`, `verdict_*`, and `closed` back to each `intent.md`. |

> **`/plan` is not part of lite-spec.** It's Claude Code's built-in planning skill. `/spec-intent` *offers* to hand a freshly-written intent to `/plan` — which drafts a regenerable `plan.md` beside `intent.md` — but the handoff is opt-in. Say no and nothing external is needed; the four `spec-*` skills above are the whole toolkit. `intent.md` always stays the source of truth, `plan.md` is a working doc.

## How it fits together

Plain Markdown, no external services. `CONSTITUTION.md` and the `INTENT/` tree are human-owned (skill-guided); each intent's optional `plan.md` is agent-writable. EARS outcomes (`WHEN <trigger> THE SYSTEM SHALL <response>`) let `spec-check` grade each SHALL against code and derive each intent's `status`.

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

Status flipped `draft → in_progress` on its own, derived from the outcome that now passes.

**4. Finish and confirm.** Write the second test, run `/spec-check` once more, and the last outcome flips:

```
## I-1: rate-limit the login endpoint  [status: complete, 2/2 outcomes passing, 2/2 by test]
Status changes this run: I-1 in_progress → complete (closed 2026-05-30).
```

You never typed `status: complete` — `spec-check` derived it from the outcomes passing. And if you'd skipped the `[test: ...]` citations entirely, I-1 would have rested at `draft` with both outcomes `unverifiable` — a [context-only intent](#context-only-intents-test-citations-are-opt-in): still a useful spec, just not a graded one.

**Why two ratios?** The header reads `2/2 outcomes passing, 2/2 by test`. The first counts every passing outcome; the second counts only those backed by a real test you can re-run. Here they match. Had an outcome instead been verified by an `agent:` check (for a SHALL no test can express — UX copy, doc structure), it would count toward the first ratio but not the second, and `spec-check` would still flip the intent to `complete` — with a one-line WARNING that the verdict leans on a weaker signal. Driving `by test` up to the full count is how you make `complete` mean *provably* complete.

## Test-backed verdicts

Each EARS outcome may carry a `[test: <runner>:<target>]` citation. When present, `spec-check` runs the citation and uses the result — not an LLM grep — to decide pass vs. fail. Two flavors of runner exist:

**Process runners** (`pytest`, `vitest`, `jest`, `cargo`, `go`, `shell`) — invoked via Bash; exit code 0 is the only path to a test-backed pass.

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

## Glossary

| Term | One-line meaning |
|---|---|
| **Intent** | One feature's spec — problem, outcomes, non-goals — in its own `I-N-<slug>/` folder. The unit of work. |
| **Outcome** | A single success criterion inside an intent, written in EARS and graded on its own. |
| **EARS** | The outcome grammar: `WHEN <trigger> THE SYSTEM SHALL <response>`. |
| **Constitution** | Project-wide principles (`P-N`) every intent is checked against. Optional. |
| **Status** | An intent's rung on `draft → in_progress → complete` (or `superseded`). Derived by `/spec-check`, never set by hand. |
| **Test citation** | A `[test: <runner>:<target>]` marker that lets `/spec-check` grade an outcome by running real code. |
| **Process runner** | A deterministic test runner (`pytest`, `vitest`, `jest`, `cargo`, `go`, `shell`). The strongest signal. |
| **Agent runner** | A subagent that grades a SHALL no test can express (UX, docs). Weaker than a process runner. |
| **Context-only intent** | An intent with no test citations — a spec you read for context, resting at `draft`. Not an error. |
| **By-test ratio** | The share of passing outcomes backed by a process-runner test. Push it toward 100%. |
| **Supersede** | Retire an intent in favor of a titled successor, preserving its history. |
