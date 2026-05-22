# Intent Doc: Lite-Spec — Claude Skills for AI-Era Spec Workflow

- **Author:** Jason Lo
- **Status:** Draft
- **Last updated:** 2026-05-22
- **Version:** v6

## Problem

The traditional spec stack (PRD → TDD → ADR → tickets) is too heavy for AI-assisted development, but teams still need structure to think clearly, align with collaborators, and preserve decisions. Open-source frameworks like GitHub Spec Kit, OpenSpec, and BMAD-METHOD prove the demand for spec-driven AI workflows but each carries significant ceremony. There is no lightweight, opinionated, Claude-native toolkit for a minimal intent → decisions → drift-check cycle.

## Outcome

A small set of Claude skills (the `ls-` family, for *lite-spec*) that together cover the full lightweight spec cycle: project principles, feature intent with testable acceptance criteria, decision logging, and drift verification. A solo developer or small team can run the entire workflow through Claude — no separate doc tool — producing durable, version-controllable, AI-readable artifacts.

- **WHEN** the user describes a new feature in loose terms **THE SYSTEM SHALL** guide them to a verified intent doc with EARS-formatted acceptance criteria.
- **WHEN** the user makes a non-trivial decision **THE SYSTEM SHALL** log it durably with rationale.
- **WHEN** intent or code changes **THE SYSTEM SHALL** detect drift between them.

## Non-Goals

- Replacing enterprise PRD tooling (Productboard, Jira, Confluence)
- Replicating heavyweight frameworks like Spec Kit or BMAD (multi-phase commands, agent personas, gated workflows)
- Regulated or safety-critical workflows requiring formal specs
- Multi-user real-time collaboration
- Project-management features (roadmaps, timelines, resource allocation)
- Generating code or task breakdowns — Claude's plan mode handles execution
- Cross-tool portability via `AGENTS.md` — explicitly Claude-first
- Automatic git hooks or CI integration — invocation stays manual
- Crash recovery, external state files, watchdog processes
- Per-skill anti-pattern refusal lists — too prescriptive, erodes the lightweight feel

## Constraints

- Max 5 skills total (currently 4); all `ls-` prefixed
- Each skill is a folder with at minimum a `SKILL.md`
- `SKILL.md` frontmatter: `name`, `description` (keyword-rich), `allowed-tools` (scoped)
- `SKILL.md` body under 5,000 words; overflow goes in `references/` (progressive disclosure)
- Acceptance criteria use EARS notation so drift checks are mechanical
- Skills are composable; output of one feeds cleanly into another
- Each skill is useful standalone — no runtime coupling
- Artifacts are plain Markdown stored in-repo; no external services or APIs
- Static typing wherever code is involved
- Simplicity over feature completeness

## The Skills

Full instructions live in each `skills/ls-*/SKILL.md`. Summary:

1. **`ls-constitution`** — creates and amends `specs/CONSTITUTION.md`. Blocking enforcement: every other skill refuses output that violates a principle. Amendments are a careful path with explicit impact surfacing.
2. **`ls-intent`** — drafts and refines `specs/INTENT.md`. Outcome section uses EARS; vague responses are rejected. Self-critique pass before finalizing. Auto-triggers `ls-check` on Change Log append.
3. **`ls-decisions`** — appends one-line decisions to `specs/DECISIONS.md` (`D-NNNN: Decided X because Y (date).`). Supersession via strikethrough plus a new entry; nothing is deleted.
4. **`ls-check`** — reads `specs/INTENT.md` + `specs/CONSTITUTION.md` + code, reports code drift, intent drift, and constitution drift. Each finding pins to a specific SHALL or principle.

## Success Metrics

- Solo developer can go from rough idea to verified implementation using only these 4 skills
- `specs/INTENT.md` body stays under ~300 words even with EARS criteria
- `specs/DECISIONS.md` entries stay under 25 words
- `specs/CONSTITUTION.md` stays under one page; amendments happen less than monthly per project
- Each `SKILL.md` body stays under 5,000 words; reference files only when needed
- `ls-check` reports cite specific SHALL statements, not overall judgments
- `ls-check` invoked at least once per feature, plus automatic invocations on Change Log entries

## Change Log

- **2026-05-22** — Initial bootstrap from intent doc v5 (Jason Lo).
- **2026-05-22** — Editorial tighten: condensed Problem/Outcome prose, collapsed "The Skills" descriptions (full text lives in each `SKILL.md`), trimmed Success Metrics. No semantic changes to EARS outcomes, Non-Goals, or Constraints (Jason Lo).
- **2026-05-22** — Moved `CONSTITUTION.md`, `INTENT.md`, `DECISIONS.md` from repo root into `specs/`; updated CLAUDE.md, README.md, and all four SKILL.md files to reference the new paths. See D-0008 for rationale (Jason Lo).
