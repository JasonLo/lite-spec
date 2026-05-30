"""Tests for the real-carrier stream parser and patch extraction.

The parser is validated against a *real* `claude --output-format stream-json`
capture (tests/fixtures/claude_stream_real.jsonl) so the trace schema can't
silently drift from what the CLI actually emits, plus an inline stream that
exercises tool_use counting and diff extraction (the real capture needed no
tools)."""
from __future__ import annotations

import json
import pathlib

from runner import run_variant
from scorers import process_metrics

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

PRICING = {
    "input_per_mtok_usd": 15.0,
    "output_per_mtok_usd": 75.0,
    "cached_input_per_mtok_usd": 1.5,
}


def test_parse_real_capture(tmp_path):
    lines = (FIXTURES / "claude_stream_real.jsonl").read_text().splitlines()
    exit_code, marker, final_text = run_variant.parse_stream(lines, tmp_path, fallback_wall=1.0)
    assert exit_code == 0
    # The real capture has a successful result event → trace is well-formed.
    events = [json.loads(l) for l in (tmp_path / "trace.jsonl").read_text().splitlines()]
    types = [e["type"] for e in events]
    assert types[0] == "tokens"
    assert "exit" in types and "turn" in types and "wall_clock" in types
    # Authoritative cost came from result.total_cost_usd → a `cost` event exists.
    cost_events = [e for e in events if e["type"] == "cost"]
    assert cost_events and cost_events[0]["usd"] > 0
    # process_metrics trusts the reported cost (rounded to 4dp), not a token estimate.
    m = process_metrics.score(tmp_path, PRICING)
    assert m["cost_usd"] == round(cost_events[0]["usd"], 4)
    assert m["result_marker_seen"] is False  # the probe never printed RESULT: done


def _stream_with_tools_and_diff() -> list[str]:
    """Synthetic stream in the real schema: two tool calls, a diff, RESULT: done."""
    return [
        json.dumps({"type": "system", "subtype": "init"}),
        json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "text", "text": "Working on it."},
                {"type": "tool_use", "name": "Edit", "input": {}},
            ]},
        }),
        json.dumps({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "ok"}]},
        }),
        json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]},
        }),
        json.dumps({
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 7,
            "duration_ms": 42000,
            "total_cost_usd": 0.512,
            "usage": {
                "input_tokens": 1200,
                "output_tokens": 800,
                "cache_read_input_tokens": 9000,
            },
            "result": "Here is the patch:\n```diff\n--- a/x.py\n+++ b/x.py\n@@\n-old\n+new\n```\nRESULT: done",
        }),
    ]


def test_parse_counts_tools_from_assistant_blocks(tmp_path):
    exit_code, marker, final_text = run_variant.parse_stream(
        _stream_with_tools_and_diff(), tmp_path, fallback_wall=99.0
    )
    assert exit_code == 0
    assert marker is True
    m = process_metrics.score(tmp_path, PRICING)
    # Two tool_use blocks across assistant messages (the user tool_result is NOT counted).
    assert m["tool_calls"] == 2
    assert m["turns"] == 7
    assert m["wall_clock_seconds"] == 42.0
    assert m["cost_usd"] == 0.512  # from total_cost_usd, not token estimate
    assert m["input_tokens"] == 1200
    assert m["cached_input_tokens"] == 9000
    assert m["result_marker_seen"] is True


def test_extract_patch_from_final_message():
    text = "blah\n```diff\n--- a/x\n+++ b/x\n@@\n-1\n+2\n```\ntrailing"
    patch = run_variant.extract_patch(text)
    assert patch.startswith("--- a/x")
    assert "+2" in patch


def test_extract_patch_absent_returns_empty():
    assert run_variant.extract_patch("no diff here") == ""


def test_run_real_writes_patch(tmp_path, monkeypatch):
    """_run_real wires the carrier output into patch.diff + a swe result, with
    the actual `claude` subprocess and worktree mechanics stubbed out."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    def fake_ensure_worktree(ref):
        wt = tmp_path / "wt"
        (wt / "skills" / "spec-init").mkdir(parents=True, exist_ok=True)
        (wt / "skills" / "spec-init" / "SKILL.md").write_text("# skill")
        return wt

    def fake_claude_print(prompt, cwd, out_dir):
        (cwd / "specs" / "INTENT").mkdir(parents=True, exist_ok=True)
        return 0, True, "done\n```diff\n--- a/f\n+++ b/f\n@@\n-x\n+y\n```\nRESULT: done"

    monkeypatch.setattr(run_variant, "ensure_worktree", fake_ensure_worktree)
    monkeypatch.setattr(run_variant, "_claude_print", fake_claude_print)

    run_variant.run("someref", {
        "repo": "r", "issue_title": "t", "issue_body_excerpt": "e",
        "intent_seed_outcome": "WHEN x THE SYSTEM SHALL y",
    }, run_dir, mock_carrier=False, skip_swe_bench=True)

    assert (run_dir / "patch.diff").read_text().startswith("--- a/f")
    swe = json.loads((run_dir / "swe_bench_result.json").read_text())
    assert swe["skipped"] is True and swe["passed"] is False
    # specs/ copied out of the sandbox.
    assert (run_dir / "specs" / "INTENT").is_dir()
