# Intent Doc: Lite-Spec — Claude Skills for AI-Era Spec Workflow

- **Author:** Jason Lo
- **Status:** Draft
- **Last updated:** 2026-05-22
- **Version:** v5

## Problem

The traditional spec stack (PRD → TDD → ADR → tickets) is too heavy for AI-assisted development, but teams still need some structure to think clearly, align with collaborators, and preserve decisions. Open-source frameworks like GitHub Spec Kit, OpenSpec, and BMAD-METHOD demonstrate strong demand for spec-driven AI workflows, but each comes with significant ceremony. There's no lightweight, opinionated Claude-native toolkit that supports a minimal intent-doc → decisions-log → drift-check cycle.

## Outcome

A small set of Claude skills (the `ls-` family, for *lite-spec*) that, used together, cover the full lightweight spec cycle: defining project principles, capturing feature intent with testable acceptance criteria, logging decisions, and continuously verifying implementation against intent. A solo developer or small team can run the entire spec workflow through Claude without touching a separate doc tool, and the artifacts produced are durable, version-controllable, and AI-readable.

- **WHEN** the user describes a new feature in loose terms **THE SYSTEM SHALL** guide them to a verified intent doc with EARS-formatted acceptance criteria.
- **WHEN** the user makes a non-trivial decision **THE SYSTEM SHALL** log it durably with rationale.
- **WHEN** intent or code changes **THE SYSTEM SHALL** detect drift between them.

## Non-Goals

- Replacing enterprise PRD tooling (Productboard, Jira, Confluence)
- Replicating heavyweight frameworks like Spec Kit or BMAD (multi-phase commands, agent personas, gated workflows)
- Supporting regulated or safety-critical workflows requiring formal specs
- Multi-user real-time collaboration features
- Project-management features (roadmaps, timelines, resource allocation)
- Generating code or task breakdowns directly — Claude's plan mode handles the execution layer
- Cross-tool portability via AGENTS.md — explicitly Claude-first
- Automatic git hooks or CI integration — invocation stays manual
- Crash recovery, external state files, or watchdog processes — out of scope
- Anti-pattern refusal lists per skill — too prescriptive, would erode the lightweight feel

## Constraints

- Maximum 5 skills total (currently using 4)
- All skill names use the `ls-` prefix
- Each skill is a folder containing at minimum a `SKILL.md`
- Each `SKILL.md` has YAML frontmatter with: `name`, `description` (keyword-rich for reliable triggering), `allowed-tools` (scoped to what the skill needs)
- Each `SKILL.md` body stays under 5,000 words; overflow goes into a `references/` subfolder loaded only when relevant (Anthropic's progressive-disclosure pattern). The `references/` folder is permitted but not required — only added when the main file approaches the cap
- Outcomes and acceptance criteria use EARS notation (`WHEN <trigger> THE SYSTEM SHALL <response>`) so drift can be verified mechanically
- Skills must be composable (output of one feeds cleanly into another)
- Artifacts are plain Markdown, stored in the repo alongside code
- No external services or APIs — everything runs through Claude + filesystem
- Each skill should be useful standalone, not require the others
- Static typing wherever code is involved
- Prefer simplicity over feature completeness

## The Skills

### 1. ls-constitution

Creates and maintains a `CONSTITUTION.md` file holding non-negotiable project principles: architectural patterns, testing standards, technology constraints, code-quality requirements. Run once per project, updated when governance changes. Principles are phrased with MUST/SHALL/NEVER, never *prefer/try to/consider*, so enforcement is unambiguous.

Enforcement is **blocking**. Every other `ls-` skill reads the constitution and refuses to produce output that violates it — `ls-intent` won't finalize an intent that contradicts a principle, `ls-decisions` won't accept a decision that breaks one. To change a principle, the user must explicitly invoke `ls-constitution` with an amendment, which triggers a "careful path": the skill surfaces what existing intents/decisions/code would be affected, requires explicit confirmation, and logs the amendment with date and rationale.

Also writes a thin pointer in `CLAUDE.md` so Claude Code picks up principles on every interaction.

### 2. ls-intent

Creates and refines the one-page intent doc (problem, outcome, non-goals, constraints, change log). Triggered when a user describes a new feature in loose terms. Output: a single `INTENT.md` file where the Outcome section uses EARS notation for acceptance criteria — each outcome is a testable statement like `WHEN <trigger> THE SYSTEM SHALL <response>`. Vague outcomes are rejected; the skill works with the user to translate "should be fast" into something like `THE SYSTEM SHALL respond to the toggle in under 100ms`.

Includes an append-only `## Change Log` section so updates are tracked without destructive edits. After drafting, automatically runs a self-critique pass — flagging vague EARS responses, missing non-goals, hidden assumptions, scope-creep risks, and unstated dependencies — and incorporates fixes before finalizing. Validates against `CONSTITUTION.md` and refuses to finalize if violations exist.

Auto-triggers `ls-check` whenever a new entry is appended to the Change Log, so drift is detected immediately after intent evolves rather than at some later manual check.

Can be re-invoked on an existing doc to re-critique.

### 3. ls-decisions

Maintains a `DECISIONS.md` file as a running log of decisions. Triggered when the user makes or describes a non-trivial choice during development. Each entry is one line: `"Decided X because Y (date)."`

Supports supersession. When a past decision is reversed, the new entry references the old one (`Supersedes D-0042: switched from REST to GraphQL because Y`) and marks the old entry inline (`~~Decided REST because X~~ [superseded by D-0073, 2026-05-22]`). Append-only history is preserved — nothing is deleted — but the current state is unambiguous.

Validates new decisions against `CONSTITUTION.md` and refuses entries that violate principles. Handles deduplication and ensures each entry is durable enough to be useful 6 months later. Maintains a thin pointer line in `CLAUDE.md` (`See DECISIONS.md for past architectural choices and rationale`) so Claude loads the full log only when needed — progressive disclosure keeps the main context lean.

### 4. ls-check

Continuously verifies code against intent. Triggered manually by the user, or automatically when `ls-intent` appends a Change Log entry. Reads `INTENT.md`, `CONSTITUTION.md`, and the relevant code, then reports three kinds of drift:

- **Code drift** — implementation no longer satisfies one or more EARS SHALL statements
- **Intent drift** — `INTENT.md` was updated but code hasn't caught up
- **Constitution drift** — feature violates a principle (e.g., principle added after feature shipped)

Because the Outcome section uses EARS, verification is mechanical: each SHALL is checked individually against the code, not vibe-checked as a whole. Output: a short checklist-style report identifying each drift type with the specific SHALL that failed and a suggested remediation.

## Success Metrics

- A solo developer can go from rough idea to verified implementation using only these 4 skills, with no other spec tooling
- Average `INTENT.md` length stays under 1 page (~300 words), even with EARS criteria
- Average `DECISIONS.md` entry under 25 words
- `CONSTITUTION.md` stays under 1 page; rarely modified after initial creation
- Constitutional amendments happen less than once per month per project (signal: principles are stable, not arbitrary)
- Each `SKILL.md` body stays under 5,000 words; reference files used only when needed
- `ls-check` reports cite specific SHALL statements rather than overall judgments (signal: EARS is doing its job)
- Users invoke `ls-check` at least once per feature, plus automatic invocations on Change Log entries

## Change Log

- **2026-05-22** — Initial bootstrap from intent doc v5 (Jason Lo).
