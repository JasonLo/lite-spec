# Project Pointers

This repo is **lite-spec**: a small set of Claude skills (`ls-constitution`, `ls-intent`, `ls-decisions`, `ls-check`) for the AI-era spec workflow.

Before generating output that touches design, architecture, or scope decisions in this repo, load these files:

- **`CONSTITUTION.md`** — non-negotiable project principles. Every skill MUST validate its output against the constitution and refuse to produce violating output.
- **`INTENT.md`** — current intent doc (problem, outcome, non-goals, constraints, change log). The Outcome section uses EARS notation.
- **`DECISIONS.md`** — append-only log of past architectural choices and rationale. Consult before re-litigating a settled question.

Skills live under `skills/ls-*/`. Each skill folder contains a `SKILL.md` with YAML frontmatter and an under-5,000-word body.
