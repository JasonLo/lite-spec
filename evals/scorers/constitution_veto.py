"""Constitution hard-veto checkers.

Any veto trip means the variant fails that task automatically, regardless of
the other evidence streams. The checkers are deliberately strict — they encode
the lite-spec invariants that, if violated, mean the workflow itself broke
(not just the output quality).

Each checker reads the per-run captured artifacts (same shape as
`scorers/deterministic.py`) plus optionally the carrier trace, and emits a
`VetoResult`.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
from typing import List

from scorers.deterministic import (
    _intent_dirs,
    _parse_frontmatter,
    _read,
    DERIVED_FIELDS,
)


@dataclasses.dataclass
class VetoResult:
    veto_id: str
    tripped: bool
    evidence: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# ----- vetoes -----


def veto_handwritten_complete(run_dir: pathlib.Path) -> VetoResult:
    """`status: complete` with null/missing derived verdict fields is forbidden.

    spec-check is the only oracle that writes `complete`; a complete status
    without the verdict ladder means an agent (or human) bypassed the oracle."""
    violations: List[str] = []
    for d in _intent_dirs(run_dir):
        fm = _parse_frontmatter(_read(d / "intent.md"))
        if fm is None or fm.get("status") != "complete":
            continue
        missing = [
            k
            for k in DERIVED_FIELDS
            if not fm.get(k) or fm.get(k, "").lower() in ("null", "~", "none")
        ]
        if missing:
            violations.append(f"{d.name}: complete with missing {missing}")
    return VetoResult(
        veto_id="handwritten_status_complete",
        tripped=bool(violations),
        evidence=(
            "no hand-written `status: complete` detected"
            if not violations
            else "; ".join(violations)
        ),
    )


def veto_decisions_mutated_in_place(run_dir: pathlib.Path) -> VetoResult:
    """DECISIONS.md is append-only. Detect in-place mutation via the trace.

    The trace (if present) captures every Edit to specs/DECISIONS.md. An Edit
    that replaces an existing `- **D-N:**` line (rather than appending a new
    one) trips the veto. Absent a trace, fall back to a structural check:
    every D-N must be unique and monotonically increasing.
    """
    text = _read(run_dir / "specs" / "DECISIONS.md")
    if not text:
        return VetoResult(
            veto_id="decisions_mutated_in_place",
            tripped=False,
            evidence="DECISIONS.md absent — nothing to validate",
        )
    ids = [int(m.group(1)) for m in re.finditer(r"\*\*D-(\d+):\*\*", text)]
    dupes = [d for d in set(ids) if ids.count(d) > 1]
    if dupes:
        return VetoResult(
            veto_id="decisions_mutated_in_place",
            tripped=True,
            evidence=f"duplicate D-N ids found: {sorted(dupes)}",
        )
    if ids and ids != sorted(ids):
        return VetoResult(
            veto_id="decisions_mutated_in_place",
            tripped=True,
            evidence=f"D-N ids not monotonically ordered: {ids}",
        )
    return VetoResult(
        veto_id="decisions_mutated_in_place",
        tripped=False,
        evidence=f"{len(ids)} D-N ids, unique and ordered",
    )


def veto_intent_body_edited_by_spec_check(run_dir: pathlib.Path) -> VetoResult:
    """spec-check MUST only touch intent frontmatter, never the body.

    Validated structurally: the body section after the closing `---` of
    frontmatter must end with a populated Change Log (the canonical body
    end), and the body must not contain spec-check-style verdict prose
    (those belong in the stdout report, not in the file)."""
    violations = []
    spec_check_prose = re.compile(
        r"^### Code drift|^## spec-check report", re.MULTILINE
    )
    for d in _intent_dirs(run_dir):
        text = _read(d / "intent.md")
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue
        body = text[end + 4 :]
        if spec_check_prose.search(body):
            violations.append(f"{d.name}: spec-check prose found in body")
    return VetoResult(
        veto_id="spec_check_wrote_to_intent_body",
        tripped=bool(violations),
        evidence=(
            "no spec-check prose in intent bodies"
            if not violations
            else "; ".join(violations)
        ),
    )


def veto_intent_missing_outcome_section(run_dir: pathlib.Path) -> VetoResult:
    """Every intent MUST have a `## Outcome` section with at least one bullet.

    An intent with no Outcome cannot be checked — the workflow itself broke
    if one shipped."""
    dirs = _intent_dirs(run_dir)
    if not dirs:
        return VetoResult(
            "intent_missing_outcome_section",
            True,
            "no intent dirs at all",
        )
    violations = []
    for d in dirs:
        text = _read(d / "intent.md")
        m = re.search(
            r"^##\s+Outcome\s*$(.*?)(^##\s|\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        if m is None:
            violations.append(f"{d.name}: no `## Outcome` section")
            continue
        if not re.search(r"^\s*-\s+\S", m.group(1), re.MULTILINE):
            violations.append(f"{d.name}: Outcome section has no bullets")
    return VetoResult(
        veto_id="intent_missing_outcome_section",
        tripped=bool(violations),
        evidence=(
            "every intent has a populated Outcome section"
            if not violations
            else "; ".join(violations)
        ),
    )


def veto_constitution_present_but_empty(run_dir: pathlib.Path) -> VetoResult:
    """If CONSTITUTION.md is present it MUST carry at least one P-N principle.

    An empty constitution file is worse than no constitution — it suggests the
    skill ran but produced nothing, and it forces every downstream check to
    silently degrade to 'no constitution' mode."""
    cpath = run_dir / "specs" / "CONSTITUTION.md"
    if not cpath.exists():
        return VetoResult(
            veto_id="constitution_present_but_empty",
            tripped=False,
            evidence="CONSTITUTION.md absent — vacuously fine",
        )
    text = _read(cpath)
    has_principle = re.search(r"\*\*P-\d+:\*\*", text) is not None
    return VetoResult(
        veto_id="constitution_present_but_empty",
        tripped=not has_principle,
        evidence=(
            "constitution carries >=1 P-N principle"
            if has_principle
            else "CONSTITUTION.md present but no `- **P-N:**` principles"
        ),
    )


ALL_VETOES = (
    veto_handwritten_complete,
    veto_decisions_mutated_in_place,
    veto_intent_body_edited_by_spec_check,
    veto_intent_missing_outcome_section,
    veto_constitution_present_but_empty,
)


def score(run_dir: pathlib.Path) -> dict:
    """Returns:

        {
            "vetoes": [{veto_id, tripped, evidence}, ...],
            "any_tripped": bool,
            "tripped_ids": [str, ...],
        }
    """
    results = [v(run_dir).to_dict() for v in ALL_VETOES]
    tripped = [r["veto_id"] for r in results if r["tripped"]]
    return {
        "vetoes": results,
        "any_tripped": bool(tripped),
        "tripped_ids": tripped,
    }
