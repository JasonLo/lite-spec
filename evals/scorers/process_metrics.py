"""Process / cost metrics from a runner trace.

The runner writes a `trace.jsonl` per (variant, task) — one JSON object per
line, with a stable shape regardless of whether the carrier was the real
`claude -p` invocation or the mock. The mock emits the same schema so the
scorer code path is identical.

Trace event schema (subset of what `claude --output-format json` emits, plus
synthesised fields):

    {"type": "turn",       "n": 3, "wall_ms": 12345}
    {"type": "tool_use",   "name": "Edit"}
    {"type": "tokens",     "input": 1234, "output": 567, "cached_input": 8000}
    {"type": "wall_clock", "seconds": 87.2}
    {"type": "cost",       "usd": 0.42}
    {"type": "exit",       "code": 0, "result_marker": "RESULT: done"}

The scorer is tolerant of missing fields (e.g. no `cached_input`) — cost is
computed from whatever was reported. If the trace carries an explicit `cost`
event (real `claude` runs report `total_cost_usd` authoritatively), that value
is used verbatim and the token-derived estimate is skipped; the mock carrier
omits the `cost` event so its cost is derived from synthesised tokens via the
budget pricing table.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Iterable


@dataclasses.dataclass
class Metrics:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    tool_calls: int
    turns: int
    wall_clock_seconds: float
    cost_usd: float
    exit_code: int | None
    result_marker_seen: bool

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _iter_events(trace_path: pathlib.Path) -> Iterable[dict]:
    if not trace_path.exists():
        return
    with trace_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int,
    input_per_mtok_usd: float,
    output_per_mtok_usd: float,
    cached_input_per_mtok_usd: float,
) -> float:
    fresh_input = max(0, input_tokens - cached_input_tokens)
    return (
        fresh_input * input_per_mtok_usd / 1_000_000
        + cached_input_tokens * cached_input_per_mtok_usd / 1_000_000
        + output_tokens * output_per_mtok_usd / 1_000_000
    )


def score(run_dir: pathlib.Path, pricing: dict) -> dict:
    """Read `run_dir/trace.jsonl` and return aggregated metrics.

    `pricing` is the dict loaded from `budget.yaml` — needs
    `input_per_mtok_usd`, `output_per_mtok_usd`, `cached_input_per_mtok_usd`.
    """
    trace = run_dir / "trace.jsonl"
    inp = out = cached = tool_calls = turns = 0
    wall = 0.0
    exit_code: int | None = None
    result_marker = False
    reported_cost: float | None = None
    for ev in _iter_events(trace):
        t = ev.get("type")
        if t == "tokens":
            inp += int(ev.get("input", 0))
            out += int(ev.get("output", 0))
            cached += int(ev.get("cached_input", 0))
        elif t == "tool_use":
            tool_calls += 1
        elif t == "turn":
            turns = max(turns, int(ev.get("n", turns + 1)))
        elif t == "wall_clock":
            wall = max(wall, float(ev.get("seconds", 0.0)))
        elif t == "cost":
            reported_cost = float(ev.get("usd", 0.0))
        elif t == "exit":
            exit_code = ev.get("code")
            if ev.get("result_marker"):
                result_marker = True
    if reported_cost is not None:
        # Real `claude` runs report total_cost_usd authoritatively — trust it
        # over the lossy 3-bucket token estimate.
        cost = reported_cost
    else:
        cost = compute_cost_usd(
            inp,
            out,
            cached,
            pricing["input_per_mtok_usd"],
            pricing["output_per_mtok_usd"],
            pricing["cached_input_per_mtok_usd"],
        )
    return Metrics(
        input_tokens=inp,
        output_tokens=out,
        cached_input_tokens=cached,
        tool_calls=tool_calls,
        turns=turns,
        wall_clock_seconds=wall,
        cost_usd=round(cost, 4),
        exit_code=exit_code,
        result_marker_seen=result_marker,
    ).to_dict()
