"""Pairwise LLM-as-judge.

Each (task, rubric-dimension) pair is judged twice with positions swapped.
A variant wins the dimension only if it wins both orderings; otherwise the
dimension is a tie. This collapses the well-documented position bias of
single-shot pairwise judging.

The judge sees four blinded artifacts per variant: `intent.md`, `DECISIONS.md`,
`CONSTITUTION.md`, and the captured `spec_check_report.md`. It is forbidden
from looking at the code patch, because rewarding judge wins for "the patch
looks better" would couple the spec-workflow score to engine-quality noise.

Caching: the rubric text and `CONSTITUTION.md` go at the head of every prompt.
The Anthropic prompt cache is a 5-minute TTL, so back-to-back judge calls (the
default in `run_pair.py`) all share a single cached prefix.

API access:
    Set ANTHROPIC_API_KEY. If unset, this module falls back to a deterministic
    stub that scores both variants tied on every dimension — useful for unit
    tests and CI-style validation.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
from typing import List, Tuple

RUBRIC_DIMENSIONS: Tuple[str, ...] = (
    "intent_clarity",
    "outcome_testability",
    "completeness",
    "brevity",
    "workflow_adherence",
)

RUBRIC_TEXT = """You are judging two variants of a lite-spec workflow output.
For each rubric dimension, decide which variant is better, or call it a tie.
Score conservatively: if you cannot point to a concrete difference, say tie.

Rubric dimensions:

1. intent_clarity — Is the `## Problem` precise? Are non-goals named?
2. outcome_testability — Are EARS outcomes specific, with `[test: ...]`
   citations pointing at concrete test files? Whole-suite citations
   (e.g. `pytest:tests/`) count against testability.
3. completeness — Is at least one `D-N` decision logged with `[intent: I-N]`?
   Is the spec-check report present and clean?
4. brevity — Is the intent body free of redundant prose? Are decisions one
   line each?
5. workflow_adherence — Does the output follow the lite-spec conventions in
   the CONSTITUTION (if provided)? Watch for hand-written `status: complete`,
   missing intent tags on decisions, or dangling `[intent: I-N]` references.

Return JSON of the form:

    {
      "intent_clarity":      {"winner": "X"|"Y"|"tie", "reason": "<one line>"},
      "outcome_testability": {"winner": "X"|"Y"|"tie", "reason": "<one line>"},
      "completeness":        {"winner": "X"|"Y"|"tie", "reason": "<one line>"},
      "brevity":             {"winner": "X"|"Y"|"tie", "reason": "<one line>"},
      "workflow_adherence":  {"winner": "X"|"Y"|"tie", "reason": "<one line>"}
    }

Do NOT use the labels "A" or "B" — use only "X" and "Y" as you see them in
this prompt. The mapping back to A/B is held by the harness."""


@dataclasses.dataclass
class JudgeResult:
    dimension: str
    winner: str  # "A", "B", or "tie"
    reason_x_first: str
    reason_y_first: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _collect_artifacts(run_dir: pathlib.Path) -> dict:
    """Pull the four artifacts shown to the judge."""
    spec = run_dir / "specs"
    intent_md = ""
    intent_dirs = sorted((spec / "INTENT").glob("I-*-*")) if (spec / "INTENT").is_dir() else []
    if intent_dirs:
        p = intent_dirs[0] / "intent.md"
        if p.exists():
            intent_md = p.read_text(encoding="utf-8")
    return {
        "intent_md": intent_md,
        "decisions_md": (spec / "DECISIONS.md").read_text(encoding="utf-8") if (spec / "DECISIONS.md").exists() else "",
        "constitution_md": (spec / "CONSTITUTION.md").read_text(encoding="utf-8") if (spec / "CONSTITUTION.md").exists() else "",
        "spec_check_report": (run_dir / "spec_check_report.md").read_text(encoding="utf-8") if (run_dir / "spec_check_report.md").exists() else "",
    }


def _build_prompt(x_artifacts: dict, y_artifacts: dict) -> str:
    return (
        f"{RUBRIC_TEXT}\n\n"
        "=== Variant X ===\n\n"
        f"--- intent.md ---\n{x_artifacts['intent_md']}\n\n"
        f"--- DECISIONS.md ---\n{x_artifacts['decisions_md']}\n\n"
        f"--- spec_check report ---\n{x_artifacts['spec_check_report']}\n\n"
        "=== Variant Y ===\n\n"
        f"--- intent.md ---\n{y_artifacts['intent_md']}\n\n"
        f"--- DECISIONS.md ---\n{y_artifacts['decisions_md']}\n\n"
        f"--- spec_check report ---\n{y_artifacts['spec_check_report']}\n\n"
        f"--- CONSTITUTION.md (shared, applies to both) ---\n"
        f"{x_artifacts['constitution_md'] or y_artifacts['constitution_md']}\n\n"
        "Return ONLY the JSON object specified in the rubric. No preamble."
    )


def _call_judge(prompt: str) -> dict:
    """Invoke Opus judge. Returns the parsed JSON or a deterministic stub
    if ANTHROPIC_API_KEY is not set."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _stub_judge(prompt)
    try:
        import anthropic
    except ImportError:
        return _stub_judge(prompt)
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": RUBRIC_TEXT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in msg.content if hasattr(block, "text"))
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return {d: {"winner": "tie", "reason": "judge returned non-JSON"} for d in RUBRIC_DIMENSIONS}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {d: {"winner": "tie", "reason": "judge JSON unparseable"} for d in RUBRIC_DIMENSIONS}


def _stub_judge(prompt: str) -> dict:
    """Deterministic stub used when no API key is available.

    Returns a verdict that's biased *only* by the lexicographic comparison of
    the two variants' intent.md hashes, so identical inputs produce identical
    ties (necessary for the negative-control test)."""
    x_block = prompt.split("=== Variant X ===")[1].split("=== Variant Y ===")[0]
    y_block = prompt.split("=== Variant Y ===")[1].split("--- CONSTITUTION.md")[0]
    if x_block.strip() == y_block.strip():
        return {d: {"winner": "tie", "reason": "stub: artifacts identical"} for d in RUBRIC_DIMENSIONS}
    # Otherwise return all-tie as well — the stub is only for plumbing.
    return {d: {"winner": "tie", "reason": "stub: judge not available"} for d in RUBRIC_DIMENSIONS}


def judge_pair(a_run_dir: pathlib.Path, b_run_dir: pathlib.Path) -> List[JudgeResult]:
    """Position-swapped pairwise judge over the rubric.

    Runs once with A=X, B=Y; runs again with A=Y, B=X. A variant wins a
    dimension only if it wins both orderings; otherwise the dimension is a
    tie."""
    a = _collect_artifacts(a_run_dir)
    b = _collect_artifacts(b_run_dir)
    forward = _call_judge(_build_prompt(a, b))   # X=A, Y=B
    reverse = _call_judge(_build_prompt(b, a))   # X=B, Y=A
    results: List[JudgeResult] = []
    for dim in RUBRIC_DIMENSIONS:
        fwd = forward.get(dim, {"winner": "tie", "reason": ""})
        rev = reverse.get(dim, {"winner": "tie", "reason": ""})
        fwd_w = fwd.get("winner", "tie")
        rev_w = rev.get("winner", "tie")
        # Forward: X=A, Y=B. So "X" means A won, "Y" means B won.
        # Reverse: X=B, Y=A. So "X" means B won, "Y" means A won.
        forward_winner = {"X": "A", "Y": "B", "tie": "tie"}.get(fwd_w, "tie")
        reverse_winner = {"X": "B", "Y": "A", "tie": "tie"}.get(rev_w, "tie")
        if forward_winner == reverse_winner and forward_winner in ("A", "B"):
            winner = forward_winner
        else:
            winner = "tie"
        results.append(
            JudgeResult(
                dimension=dim,
                winner=winner,
                reason_x_first=fwd.get("reason", ""),
                reason_y_first=rev.get("reason", ""),
            )
        )
    return results


def score(a_run_dir: pathlib.Path, b_run_dir: pathlib.Path) -> dict:
    results = [r.to_dict() for r in judge_pair(a_run_dir, b_run_dir)]
    a_wins = sum(1 for r in results if r["winner"] == "A")
    b_wins = sum(1 for r in results if r["winner"] == "B")
    ties = sum(1 for r in results if r["winner"] == "tie")
    total = len(results)
    return {
        "dimensions": results,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "total": total,
        "a_win_rate": a_wins / total if total else 0.0,
        "b_win_rate": b_wins / total if total else 0.0,
    }
