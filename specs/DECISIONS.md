# Decisions Log

Append-only log of non-trivial decisions. Each entry is one line: `D-NNNN: Decided X because Y (YYYY-MM-DD).` Supersede with `Supersedes D-NNNN: ...` and strike the prior entry inline.

- **D-0001:** Decided to ship 4 skills (`ls-constitution`, `ls-intent`, `ls-decisions`, `ls-check`) rather than the 5-skill cap because the lightweight cycle is already complete without a fifth (2026-05-22).
- **D-0002:** Decided on `ls-` prefix for all skills because it groups them in skill listings and signals "lite-spec" lineage (2026-05-22).
- **D-0003:** Decided EARS notation (`WHEN <trigger> THE SYSTEM SHALL <response>`) for acceptance criteria because it makes drift checks mechanical rather than vibe-based (2026-05-22).
- **D-0004:** Decided Markdown-only artifacts stored in-repo because they version-control cleanly and need no external service (2026-05-22).
- **D-0005:** Decided Claude-first (no `AGENTS.md`) because cross-tool portability would force lowest-common-denominator instructions and erode the opinionated lightweight feel (2026-05-22).
- **D-0006:** Decided constitutional enforcement is blocking (skills refuse violating output) rather than advisory because advisory rules drift to ignored rules (2026-05-22).
- **D-0007:** Decided `ls-intent` auto-invokes `ls-check` on every Change Log append because drift detected immediately after intent evolution is cheaper than drift discovered weeks later (2026-05-22).
- **D-0008:** Decided to store the three artifact docs under `specs/` rather than the repo root because it groups spec material in one place and keeps the root readable as project surface area grows (2026-05-22).
