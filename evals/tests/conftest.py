"""Pytest fixtures for the eval harness tests.

Each fixture builds a tiny on-disk run_dir under a tmp path so the scorers can
read it the same way they will at runtime."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

# Make `from scorers.X` etc. resolve when running from evals/.
EVALS_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALS_ROOT))


def _write_intent(
    root: pathlib.Path,
    intent_id: str,
    slug: str,
    status: str,
    *,
    with_ears: bool = True,
    with_test_citation: bool = True,
    with_outcome_section: bool = True,
    verdict_passed: int | None = 1,
    verdict_total: int | None = 1,
    verdict_checked_at: str | None = "2026-05-24T00:00:00Z",
    body_extra: str = "",
) -> None:
    d = root / "specs" / "INTENT" / f"{intent_id}-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    ears = "WHEN the user does X THE SYSTEM SHALL respond with Y" if with_ears else "the system does X"
    cite = " [test: pytest:tests/test_x.py::test_y]" if with_test_citation else ""
    outcome_section = "## Outcome\n\n- " + ears + cite + "\n\n" if with_outcome_section else ""

    def yv(v):
        return "null" if v is None else v

    parts = [
        "---",
        f"id: {intent_id}",
        "title: test",
        f"slug: {slug}",
        f"status: {status}",
        "opened: 2026-05-24",
        "closed: null",
        "superseded_by: null",
        f"verdict_outcomes_passed: {yv(verdict_passed)}",
        f"verdict_outcomes_total: {yv(verdict_total)}",
        f"verdict_outcomes_passed_by_test: {yv(verdict_passed)}",
        f"verdict_checked_at: {yv(verdict_checked_at)}",
        "---",
        "",
        "# Intent: test",
        "",
        "## Problem",
        "test problem",
        "",
        outcome_section.rstrip("\n"),
        "",
        "## Non-Goals",
        "- none",
        "",
        "## Constraints",
        "- none",
        "",
        "## Change Log",
        "- 2026-05-24 — init",
        body_extra,
        "",
    ]
    (d / "intent.md").write_text("\n".join(parts))


def _write_decisions(root: pathlib.Path, entries: list[str]) -> None:
    body = "# Decisions Log\n\nAppend-only log.\n\n" + "\n".join(entries) + "\n"
    (root / "specs" / "DECISIONS.md").write_text(body)


def _write_constitution(root: pathlib.Path, principles: list[str]) -> None:
    body = (
        "# Constitution: test\n\nRatified: 2026-05-24\n\n## Artifacts\n\n"
        + "\n".join(principles)
        + "\n"
    )
    (root / "specs" / "CONSTITUTION.md").write_text(body)


def _write_spec_check_report(root: pathlib.Path, status: str = "complete") -> None:
    (root / "spec_check_report.md").write_text(
        f"# spec-check report — 2026-05-24\n\n"
        f"## I-1: test  [status: {status}, 1/1 outcomes passing]\n\n"
        f"### Code drift\n"
        f"- [x] O-1: pass (test).\n\n"
        f"## Summary\nIntents checked: 1.\n"
    )


def _write_trace(root: pathlib.Path, *, input_tokens=5000, output_tokens=1000, cached=3000, tool_calls=8, turns=5, wall=120.0, exit_code=0) -> None:
    events = [
        {"type": "tokens", "input": input_tokens, "output": output_tokens, "cached_input": cached},
        *[{"type": "tool_use", "name": "Edit"} for _ in range(tool_calls)],
        {"type": "turn", "n": turns, "wall_ms": int(wall * 1000)},
        {"type": "wall_clock", "seconds": wall},
        {"type": "exit", "code": exit_code, "result_marker": True},
    ]
    with (root / "trace.jsonl").open("w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


@pytest.fixture
def good_run(tmp_path: pathlib.Path) -> pathlib.Path:
    """A clean, lite-spec-compliant run."""
    (tmp_path / "specs").mkdir()
    _write_intent(tmp_path, "I-1", "feature-x", "complete")
    _write_decisions(tmp_path, ["- **D-1:** Chose pytest fixtures (2026-05-24). [intent: I-1]"])
    _write_constitution(
        tmp_path,
        [
            "- **P-1:** EARS outcomes MUST carry [test: ...] citations.",
            "- **P-2:** Decisions MUST carry [intent: I-N] tags.",
        ],
    )
    _write_spec_check_report(tmp_path)
    _write_trace(tmp_path)
    return tmp_path


@pytest.fixture
def handwritten_complete_run(tmp_path: pathlib.Path) -> pathlib.Path:
    """A run where status=complete but verdict fields are null — should trip veto."""
    (tmp_path / "specs").mkdir()
    _write_intent(
        tmp_path,
        "I-1",
        "feature-x",
        "complete",
        verdict_passed=None,
        verdict_total=None,
        verdict_checked_at=None,
    )
    _write_decisions(tmp_path, ["- **D-1:** Trivial choice (2026-05-24). [intent: I-1]"])
    _write_constitution(tmp_path, ["- **P-1:** EARS outcomes MUST carry citations."])
    _write_spec_check_report(tmp_path)
    _write_trace(tmp_path)
    return tmp_path


@pytest.fixture
def untagged_decisions_run(tmp_path: pathlib.Path) -> pathlib.Path:
    """A run where DECISIONS entries lack [intent: I-N] tags."""
    (tmp_path / "specs").mkdir()
    _write_intent(tmp_path, "I-1", "feature-x", "complete")
    _write_decisions(tmp_path, ["- **D-1:** Made a choice (2026-05-24).", "- **D-2:** Another (2026-05-24). [intent: I-1]"])
    _write_constitution(tmp_path, ["- **P-1:** EARS outcomes MUST carry citations."])
    _write_spec_check_report(tmp_path)
    _write_trace(tmp_path)
    return tmp_path


@pytest.fixture
def no_outcome_run(tmp_path: pathlib.Path) -> pathlib.Path:
    """A run where intent has no `## Outcome` section — trips outcome veto."""
    (tmp_path / "specs").mkdir()
    _write_intent(tmp_path, "I-1", "feature-x", "draft", with_outcome_section=False)
    _write_decisions(tmp_path, ["- **D-1:** Trivial (2026-05-24). [intent: I-1]"])
    _write_constitution(tmp_path, ["- **P-1:** principle."])
    _write_spec_check_report(tmp_path, status="draft")
    _write_trace(tmp_path)
    return tmp_path


@pytest.fixture
def pricing() -> dict:
    return {
        "input_per_mtok_usd": 15.0,
        "output_per_mtok_usd": 75.0,
        "cached_input_per_mtok_usd": 1.5,
    }
