"""Integration test for run_pair's real-carrier glue.

Stubs the `claude` subprocess (via run_variant._claude_print) and the worktree
so the full A/B loop — variant runs, four scorers, director, verdict.md — is
exercised without API spend or Docker, and asserts that SWE-bench auto-skips
when no Docker daemon is reachable."""
from __future__ import annotations

import json
import pathlib
import sys

from runner import run_pair, run_variant, sandbox


def _fake_carrier_output(cwd: pathlib.Path, ref: str):
    """Write a compliant specs/ tree into the sandbox, mimicking a lite-spec run."""
    intent = cwd / "specs" / "INTENT" / "I-1-feature"
    intent.mkdir(parents=True, exist_ok=True)
    (intent / "intent.md").write_text(
        "---\nid: I-1\ntitle: t\nslug: feature\nstatus: in_progress\n"
        "opened: 2026-05-24\nclosed: null\nsuperseded_by: null\n"
        "verdict_outcomes_passed: 0\nverdict_outcomes_total: 1\n"
        "verdict_outcomes_passed_by_test: 0\nverdict_checked_at: null\n---\n\n"
        "# Intent: t\n\n## Problem\np\n\n## Outcome\n\n"
        "- WHEN x THE SYSTEM SHALL y [test: pytest:tests/test_x.py::test_y]\n\n"
        "## Non-Goals\n- none\n\n## Constraints\n- none\n\n## Change Log\n- 2026-05-24 — init\n"
    )
    (cwd / "specs" / "DECISIONS.md").write_text(
        "# Decisions Log\n\n- **D-1:** chose approach (2026-05-24). [intent: I-1]\n"
    )
    (cwd / "specs" / "CONSTITUTION.md").write_text(
        "# Constitution\n\n## Artifacts\n\n- **P-1:** EARS outcomes MUST carry [test: ...].\n"
    )


def test_run_pair_real_path_autoskips_swe(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "docker_available", lambda: False)

    def fake_ensure_worktree(ref):
        wt = tmp_path / f"wt-{ref}"
        (wt / "skills" / "spec-init").mkdir(parents=True, exist_ok=True)
        (wt / "skills" / "spec-init" / "SKILL.md").write_text("# skill")
        return wt

    def fake_claude_print(prompt, cwd, out_dir):
        _fake_carrier_output(cwd, "x")
        run_variant.parse_stream(
            [json.dumps({
                "type": "result", "subtype": "success", "is_error": False,
                "num_turns": 5, "duration_ms": 30000, "total_cost_usd": 0.25,
                "usage": {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 2000},
                "result": "```diff\n--- a/f\n+++ b/f\n@@\n-x\n+y\n```\nRESULT: done",
            })],
            out_dir,
            fallback_wall=30.0,
        )
        return 0, True, "```diff\n--- a/f\n+++ b/f\n@@\n-x\n+y\n```\nRESULT: done"

    monkeypatch.setattr(run_variant, "ensure_worktree", fake_ensure_worktree)
    monkeypatch.setattr(run_variant, "_claude_print", fake_claude_print)

    report_dir = run_pair.EVALS_ROOT / "reports" / "pytest-realglue"
    monkeypatch.setattr(
        sys, "argv",
        [
            "run_pair",
            "--variants", str(_write_manifest(tmp_path)),
            "--tasks", str(run_pair.EVALS_ROOT / "tasks" / "swe-bench-lite-subset.jsonl"),
            "--budget", "shoestring",
            "--no-mock-carrier",
            "--report-id", "pytest-realglue",
        ],
    )
    rc = run_pair.main()
    assert rc == 0
    scores = json.loads((report_dir / "scores.json").read_text())
    # Every task's SWE result was auto-skipped (Docker down), so swe stream is neutral.
    for row in scores["raw"]:
        assert row["a"]["swe_bench"]["skipped"] is True
        assert row["b"]["swe_bench"]["skipped"] is True
    # A==B refs → symmetric artifacts → no decisive winner.
    assert scores["verdict"]["verdict"] == "inconclusive"
    assert (report_dir / "verdict.md").exists()


def _write_manifest(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"name": "pytest-real-glue", "a": "refA", "b": "refB"}))
    return p
