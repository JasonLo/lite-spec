"""Deterministic spec-adherence checks.

Each rule reads the captured `specs/` tree (plus the spec-check report) for one
variant-task run and emits `{rule_id, passed, evidence}`. No LLM calls. The
rules encode lite-spec's own conventions; they must stay in sync with the
SKILL.md prompts as those conventions evolve.

Inputs (directory layout under `run_dir`):
    run_dir/
        specs/CONSTITUTION.md            (optional)
        specs/INTENT/I-N-<slug>/intent.md
        specs/DECISIONS.md               (optional)
        spec_check_report.md             (captured stdout of /spec-check)
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
from typing import List

EARS_PATTERN = re.compile(
    r"\bWHEN\b.*\bTHE\s+SYSTEM\s+SHALL\b", re.IGNORECASE | re.DOTALL
)
# A valid intent tag is either `[intent: I-N]` (tied to a feature intent) or
# `[intent: none]` (a project-level decision not scoped to any single intent).
# Both count as tagged; only a missing tag is an adherence failure.
INTENT_TAG_PATTERN = re.compile(r"\[intent:\s*(?:I-\d+|none)\]")
TEST_CITATION_PATTERN = re.compile(
    r"\[test:\s*(pytest|vitest|jest|cargo|go|shell|agent):"
)
DECISION_LINE_PATTERN = re.compile(r"^\s*-\s+\*\*D-\d+:\*\*", re.MULTILINE)
ALLOWED_STATUSES = {"draft", "in_progress", "complete", "superseded"}
DERIVED_FIELDS = (
    "verdict_outcomes_passed",
    "verdict_outcomes_total",
    "verdict_checked_at",
)


@dataclasses.dataclass
class RuleResult:
    rule_id: str
    passed: bool
    evidence: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _read(p: pathlib.Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _parse_frontmatter(text: str) -> dict | None:
    """Minimal YAML-frontmatter parser. Returns None if missing or malformed.

    Kept stdlib-only on purpose — we want adherence checks to run without a
    YAML dep so failures here are about the artifact, never about tooling."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body = text[3:end].strip()
    out: dict = {}
    for line in body.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            return None
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip()
    return out


def _intent_dirs(run_dir: pathlib.Path) -> List[pathlib.Path]:
    intent_root = run_dir / "specs" / "INTENT"
    if not intent_root.is_dir():
        return []
    return sorted(p for p in intent_root.glob("I-*-*") if p.is_dir())


# ----- individual rules -----


def rule_intent_exists(run_dir: pathlib.Path) -> RuleResult:
    dirs = _intent_dirs(run_dir)
    return RuleResult(
        rule_id="intent_exists",
        passed=len(dirs) >= 1,
        evidence=f"found {len(dirs)} intent dir(s) under specs/INTENT/",
    )


def rule_intent_has_ears(run_dir: pathlib.Path) -> RuleResult:
    dirs = _intent_dirs(run_dir)
    if not dirs:
        return RuleResult("intent_has_ears", False, "no intent dir present")
    misses = []
    for d in dirs:
        intent = _read(d / "intent.md")
        if not EARS_PATTERN.search(intent):
            misses.append(d.name)
    return RuleResult(
        rule_id="intent_has_ears",
        passed=not misses,
        evidence=(
            "all intents carry >=1 EARS SHALL"
            if not misses
            else f"missing EARS in: {', '.join(misses)}"
        ),
    )


def rule_intent_has_test_citation(run_dir: pathlib.Path) -> RuleResult:
    dirs = _intent_dirs(run_dir)
    if not dirs:
        return RuleResult("intent_has_test_citation", False, "no intent dir")
    misses = []
    for d in dirs:
        intent = _read(d / "intent.md")
        if not TEST_CITATION_PATTERN.search(intent):
            misses.append(d.name)
    return RuleResult(
        rule_id="intent_has_test_citation",
        passed=not misses,
        evidence=(
            "all intents carry >=1 [test: ...] citation"
            if not misses
            else f"missing [test: ...] in: {', '.join(misses)}"
        ),
    )


def rule_frontmatter_valid(run_dir: pathlib.Path) -> RuleResult:
    dirs = _intent_dirs(run_dir)
    if not dirs:
        return RuleResult("frontmatter_valid", False, "no intent dir")
    problems = []
    for d in dirs:
        fm = _parse_frontmatter(_read(d / "intent.md"))
        if fm is None:
            problems.append(f"{d.name}: frontmatter unparseable or missing")
            continue
        status = fm.get("status")
        if status and status not in ALLOWED_STATUSES:
            problems.append(f"{d.name}: status={status!r} not in allowed set")
    return RuleResult(
        rule_id="frontmatter_valid",
        passed=not problems,
        evidence=(
            "all frontmatter parseable with allowed status"
            if not problems
            else "; ".join(problems)
        ),
    )


def rule_status_derived_not_handwritten(run_dir: pathlib.Path) -> RuleResult:
    """If status==complete, derived verdict fields must be present and consistent.

    spec-check is the only writer of `status: complete`; a complete status with
    null/missing verdict fields means a human (or agent) hand-wrote it."""
    dirs = _intent_dirs(run_dir)
    if not dirs:
        return RuleResult(
            "status_derived_not_handwritten", False, "no intent dir"
        )
    violations = []
    for d in dirs:
        fm = _parse_frontmatter(_read(d / "intent.md"))
        if fm is None or fm.get("status") != "complete":
            continue
        for k in DERIVED_FIELDS:
            v = fm.get(k)
            if not v or v.lower() in ("null", "~", "none"):
                violations.append(f"{d.name}: status=complete but {k}={v!r}")
                break
    return RuleResult(
        rule_id="status_derived_not_handwritten",
        passed=not violations,
        evidence=(
            "no hand-written `status: complete`"
            if not violations
            else "; ".join(violations)
        ),
    )


def rule_decisions_tagged(run_dir: pathlib.Path) -> RuleResult:
    dec = run_dir / "specs" / "DECISIONS.md"
    text = _read(dec)
    if not text:
        return RuleResult(
            "decisions_tagged",
            False,
            "specs/DECISIONS.md missing or empty",
        )
    lines = [ln for ln in text.splitlines() if DECISION_LINE_PATTERN.match(ln)]
    if not lines:
        return RuleResult(
            "decisions_tagged",
            False,
            "DECISIONS.md has no `- **D-N:**` entries",
        )
    untagged = [
        ln for ln in lines if not INTENT_TAG_PATTERN.search(ln)
    ]
    return RuleResult(
        rule_id="decisions_tagged",
        passed=not untagged,
        evidence=(
            f"all {len(lines)} decision entries carry [intent: I-N]"
            if not untagged
            else f"{len(untagged)}/{len(lines)} entries missing [intent: ...]"
        ),
    )


def rule_decisions_at_least_one(run_dir: pathlib.Path) -> RuleResult:
    dec = run_dir / "specs" / "DECISIONS.md"
    text = _read(dec)
    lines = [ln for ln in text.splitlines() if DECISION_LINE_PATTERN.match(ln)]
    return RuleResult(
        rule_id="decisions_at_least_one",
        passed=len(lines) >= 1,
        evidence=f"{len(lines)} D-N entries present",
    )


def rule_spec_check_ran(run_dir: pathlib.Path) -> RuleResult:
    rpt = run_dir / "spec_check_report.md"
    text = _read(rpt)
    if not text:
        return RuleResult(
            "spec_check_ran",
            False,
            "spec_check_report.md missing or empty",
        )
    looks_like_report = "spec-check report" in text.lower() or "## I-" in text
    return RuleResult(
        rule_id="spec_check_ran",
        passed=looks_like_report,
        evidence=(
            "spec-check report captured"
            if looks_like_report
            else "report file present but content does not look like spec-check stdout"
        ),
    )


def rule_no_dangling_intent_tags(run_dir: pathlib.Path) -> RuleResult:
    dec = run_dir / "specs" / "DECISIONS.md"
    text = _read(dec)
    if not text:
        return RuleResult(
            "no_dangling_intent_tags",
            True,
            "DECISIONS.md absent — nothing to validate",
        )
    intent_dirs = {p.name.split("-")[1] for p in _intent_dirs(run_dir)}
    referenced = set()
    for m in re.finditer(r"\[intent:\s*I-(\d+)\]", text):
        referenced.add(m.group(1))
    dangling = sorted(referenced - intent_dirs)
    return RuleResult(
        rule_id="no_dangling_intent_tags",
        passed=not dangling,
        evidence=(
            "all [intent: I-N] tags resolve to intent dirs"
            if not dangling
            else f"dangling references: I-{', I-'.join(dangling)}"
        ),
    )


ALL_RULES = (
    rule_intent_exists,
    rule_intent_has_ears,
    rule_intent_has_test_citation,
    rule_frontmatter_valid,
    rule_status_derived_not_handwritten,
    rule_decisions_at_least_one,
    rule_decisions_tagged,
    rule_no_dangling_intent_tags,
    rule_spec_check_ran,
)


def score(run_dir: pathlib.Path) -> dict:
    """Run every adherence rule against `run_dir`. Returns:

        {
            "rules": [{rule_id, passed, evidence}, ...],
            "pass_count": int,
            "total": int,
            "pass_rate": float,    # 0..1
        }
    """
    results = [rule(run_dir).to_dict() for rule in ALL_RULES]
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "rules": results,
        "pass_count": passed,
        "total": total,
        "pass_rate": passed / total if total else 0.0,
    }
