# Lite-Spec Constitution

Non-negotiable principles for this project. Every `ls-` skill MUST validate its output against this file and refuse to produce output that violates a principle. To change a principle, invoke `ls-constitution` with an amendment — never edit silently.

## Scope and Surface Area

1. **The toolkit MUST consist of at most 5 skills.** Currently 4: `ls-constitution`, `ls-intent`, `ls-decisions`, `ls-check`. Adding a 6th skill requires a constitutional amendment.
2. **Every skill name MUST use the `ls-` prefix.** No exceptions.
3. **Each skill MUST be a folder containing at minimum a `SKILL.md`.** Additional files (templates, references) are permitted but not required.
4. **Each skill MUST be useful standalone.** No skill MAY hard-require another skill to function. Composition is encouraged; coupling is forbidden.

## Skill File Format

5. **Every `SKILL.md` MUST have YAML frontmatter with `name`, `description`, and `allowed-tools`.** The `description` MUST be keyword-rich for reliable triggering. The `allowed-tools` list MUST be scoped to what the skill actually needs.
6. **Every `SKILL.md` body MUST stay under 5,000 words.** Overflow MUST go into a `references/` subfolder and be loaded only when relevant (progressive disclosure). The `references/` folder is permitted but NOT required.
7. **Skill instructions MUST be written in imperative MUST/SHALL/NEVER form.** NEVER use *prefer/try to/consider* — enforcement is unambiguous or it is nothing.

## Artifacts

8. **All artifacts MUST be plain Markdown stored in the repo alongside code.** NEVER write to external services, databases, or APIs.
9. **Acceptance criteria MUST use EARS notation:** `WHEN <trigger> THE SYSTEM SHALL <response>`. Vague responses (e.g., "should be fast") MUST be rejected and rewritten with a measurable threshold.
10. **`INTENT.md`, `DECISIONS.md`, and `CONSTITUTION.md` MUST be append-only for historical sections.** Existing Change Log entries, decision entries, and amendment entries MUST NEVER be deleted — supersession is the only mechanism for reversal.

## Boundaries

11. **The toolkit MUST be Claude-first.** NEVER add `AGENTS.md` or other cross-tool portability layers.
12. **Invocation MUST stay manual.** NEVER add automatic git hooks, CI integration, watchdog processes, or external state files. The only exception is `ls-intent` auto-triggering `ls-check` after a Change Log append, which is in-process, not an external hook.
13. **The toolkit MUST NOT replace enterprise PRD tooling, project management, or regulated/safety-critical workflows.** Out of scope is out of scope.

## Code Quality

14. **All code MUST be statically typed in its language of choice.** No untyped JavaScript, no untyped Python, no `any`-equivalents in load-bearing positions.
15. **Simplicity MUST win over feature completeness.** When in doubt, ship the smaller version.

## Amendments

- **2026-05-22** — Initial constitution ratified from intent doc v5 constraints.
