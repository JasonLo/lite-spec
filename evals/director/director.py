"""Deterministic aggregator + verdict.md emitter.

The director is NOT another LLM. It mechanically combines the four evidence
streams using frozen weights and emits an accept / reject / inconclusive
verdict.

Frozen weights (any change here is itself a methodology change and must land
in a separate PR from a delta evaluation — never tune these for a specific
delta):

    score = 0.4 * adherence_pass_rate
          + 0.3 * judge_win              # 1.0 if variant won judge for this task, 0.0 ties, 0.0 lost
          + 0.2 * swe_bench_pass         # 1.0 if the carrier task passed, 0.0 otherwise
          + 0.1 * cost_score             # 1 - min(cost / max_cost, 1.0); cheaper = higher

Verdict logic (in order):

    1. If either variant trips a constitution veto on a task, that variant
       loses that task automatically — task winner is the other variant (or
       "both vetoed" → no winner).
    2. Otherwise, compute per-task weighted scores; higher wins.
    3. Aggregate verdict:
       - B accepted iff: B wins >= ceil(N/2 + 1) tasks (strict majority of
         margin >=1) AND no B veto trips AND B judge-win rate >= 60% AND
         no evidence stream regresses by >20pp average.
       - Otherwise reject if A wins majority by the same criteria.
       - Otherwise inconclusive.
"""
from __future__ import annotations

import dataclasses
import math
import pathlib
from typing import Dict, List, Optional, Tuple

WEIGHTS = {
    "adherence": 0.4,
    "judge": 0.3,
    "swe_bench": 0.2,
    "cost": 0.1,
}
JUDGE_WIN_THRESHOLD = 0.6
REGRESSION_TOLERANCE_PP = 0.20  # 20pp


@dataclasses.dataclass
class TaskScores:
    task_id: str
    a_adherence: float
    b_adherence: float
    judge_winner: str  # "A", "B", or "tie"
    a_swe_bench_pass: bool
    b_swe_bench_pass: bool
    a_cost: float
    b_cost: float
    a_veto_tripped: bool
    b_veto_tripped: bool
    a_veto_ids: List[str]
    b_veto_ids: List[str]


@dataclasses.dataclass
class DirectorVerdict:
    verdict: str  # "accept_b", "reject_b", "inconclusive"
    rationale: str
    per_task: List[dict]
    aggregate: dict


def _judge_win_score(judge_winner: str, variant: str) -> float:
    return 1.0 if judge_winner == variant else 0.0


def _cost_score(cost: float, max_cost: float) -> float:
    if max_cost <= 0:
        return 1.0
    return max(0.0, 1.0 - cost / max_cost)


def _weighted_score(
    adherence: float,
    judge_win: float,
    swe_pass: bool,
    cost_score: float,
) -> float:
    return (
        WEIGHTS["adherence"] * adherence
        + WEIGHTS["judge"] * judge_win
        + WEIGHTS["swe_bench"] * (1.0 if swe_pass else 0.0)
        + WEIGHTS["cost"] * cost_score
    )


def _per_task_winner(ts: TaskScores, max_cost: float) -> Tuple[Optional[str], float, float, str]:
    # Hard veto step.
    if ts.a_veto_tripped and ts.b_veto_tripped:
        return None, 0.0, 0.0, "both vetoed"
    if ts.a_veto_tripped:
        return "B", 0.0, _weighted_score(
            ts.b_adherence,
            _judge_win_score(ts.judge_winner, "B"),
            ts.b_swe_bench_pass,
            _cost_score(ts.b_cost, max_cost),
        ), f"A veto: {','.join(ts.a_veto_ids)}"
    if ts.b_veto_tripped:
        return "A", _weighted_score(
            ts.a_adherence,
            _judge_win_score(ts.judge_winner, "A"),
            ts.a_swe_bench_pass,
            _cost_score(ts.a_cost, max_cost),
        ), 0.0, f"B veto: {','.join(ts.b_veto_ids)}"
    a = _weighted_score(
        ts.a_adherence,
        _judge_win_score(ts.judge_winner, "A"),
        ts.a_swe_bench_pass,
        _cost_score(ts.a_cost, max_cost),
    )
    b = _weighted_score(
        ts.b_adherence,
        _judge_win_score(ts.judge_winner, "B"),
        ts.b_swe_bench_pass,
        _cost_score(ts.b_cost, max_cost),
    )
    if abs(a - b) < 1e-9:
        return "tie", a, b, "weighted score tied"
    return ("A" if a > b else "B"), a, b, "weighted score"


def _stream_regression(per_task: List[dict], variant: str, other: str) -> Dict[str, float]:
    """Average per-task delta `variant - other` per evidence stream. Negative
    means `variant` regressed against `other` on that stream."""
    if not per_task:
        return {}

    def avg(key_v: str, key_o: str) -> float:
        n = len(per_task)
        return sum(p[key_v] - p[key_o] for p in per_task) / n

    return {
        "adherence_delta": avg(f"{variant.lower()}_adherence", f"{other.lower()}_adherence"),
        "swe_bench_delta": avg(f"{variant.lower()}_swe_bench", f"{other.lower()}_swe_bench"),
        "cost_delta": avg(f"{variant.lower()}_cost_score", f"{other.lower()}_cost_score"),
    }


def aggregate(task_scores: List[TaskScores]) -> DirectorVerdict:
    """Produce the final verdict."""
    if not task_scores:
        return DirectorVerdict(
            verdict="inconclusive",
            rationale="no task scores",
            per_task=[],
            aggregate={},
        )
    # Normalize cost across the pool so the cost_score weight isn't dominated
    # by the largest absolute cost.
    max_cost = max(
        [ts.a_cost for ts in task_scores] + [ts.b_cost for ts in task_scores] + [1e-6]
    )
    per_task_rows: List[dict] = []
    a_wins = b_wins = ties = no_winner = 0
    a_vetoes = b_vetoes = 0
    judge_b_wins = 0
    judge_decisive = 0  # judged dimensions that weren't ties or unknowns
    for ts in task_scores:
        winner, a_score, b_score, reason = _per_task_winner(ts, max_cost)
        if winner == "A":
            a_wins += 1
        elif winner == "B":
            b_wins += 1
        elif winner == "tie":
            ties += 1
        else:
            no_winner += 1
        if ts.a_veto_tripped:
            a_vetoes += 1
        if ts.b_veto_tripped:
            b_vetoes += 1
        if ts.judge_winner in ("A", "B"):
            judge_decisive += 1
            if ts.judge_winner == "B":
                judge_b_wins += 1
        per_task_rows.append(
            {
                "task_id": ts.task_id,
                "winner": winner,
                "a_score": round(a_score, 4),
                "b_score": round(b_score, 4),
                "a_adherence": ts.a_adherence,
                "b_adherence": ts.b_adherence,
                "a_swe_bench": 1.0 if ts.a_swe_bench_pass else 0.0,
                "b_swe_bench": 1.0 if ts.b_swe_bench_pass else 0.0,
                "a_cost_score": _cost_score(ts.a_cost, max_cost),
                "b_cost_score": _cost_score(ts.b_cost, max_cost),
                "judge_winner": ts.judge_winner,
                "reason": reason,
            }
        )

    n = len(task_scores)
    needed = math.ceil(n / 2 + 1) if n > 1 else 1
    judge_b_rate = judge_b_wins / judge_decisive if judge_decisive else 0.0
    judge_a_rate = (judge_decisive - judge_b_wins) / judge_decisive if judge_decisive else 0.0

    b_regressions = _stream_regression(per_task_rows, "B", "A")
    a_regressions = _stream_regression(per_task_rows, "A", "B")

    def regressed_streams(deltas: Dict[str, float]) -> List[str]:
        # Negative delta beyond tolerance == regression.
        return [k for k, v in deltas.items() if v < -REGRESSION_TOLERANCE_PP]

    b_regressed = regressed_streams(b_regressions)
    a_regressed = regressed_streams(a_regressions)

    rationale_parts: List[str] = []
    verdict = "inconclusive"

    if b_wins >= needed and b_vetoes == 0 and judge_b_rate >= JUDGE_WIN_THRESHOLD and not b_regressed:
        verdict = "accept_b"
        rationale_parts.append(
            f"B wins {b_wins}/{n} (need {needed}); judge B rate {judge_b_rate:.0%} >= {JUDGE_WIN_THRESHOLD:.0%}; "
            f"0 B vetoes; no >20pp regression."
        )
    elif a_wins >= needed and a_vetoes == 0 and judge_a_rate >= JUDGE_WIN_THRESHOLD and not a_regressed:
        verdict = "reject_b"
        rationale_parts.append(
            f"A wins {a_wins}/{n} (need {needed}); judge A rate {judge_a_rate:.0%} >= {JUDGE_WIN_THRESHOLD:.0%}; "
            f"0 A vetoes; no >20pp regression."
        )
    else:
        verdict = "inconclusive"
        if b_wins < needed and a_wins < needed:
            rationale_parts.append(
                f"neither variant wins a strict majority (A={a_wins}, B={b_wins}, tie={ties}, no-winner={no_winner}, need {needed})"
            )
        if b_vetoes:
            rationale_parts.append(f"B tripped vetoes on {b_vetoes} task(s)")
        if a_vetoes:
            rationale_parts.append(f"A tripped vetoes on {a_vetoes} task(s)")
        if judge_decisive and judge_b_rate < JUDGE_WIN_THRESHOLD and judge_a_rate < JUDGE_WIN_THRESHOLD:
            rationale_parts.append(
                f"judge win rates below {JUDGE_WIN_THRESHOLD:.0%} (A={judge_a_rate:.0%}, B={judge_b_rate:.0%})"
            )
        if b_regressed:
            rationale_parts.append(f"B regressed on streams: {','.join(b_regressed)}")
        if a_regressed:
            rationale_parts.append(f"A regressed on streams: {','.join(a_regressed)}")

    aggregate_summary = {
        "n_tasks": n,
        "needed_for_majority": needed,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "no_winner": no_winner,
        "a_veto_count": a_vetoes,
        "b_veto_count": b_vetoes,
        "judge_decisive": judge_decisive,
        "judge_a_win_rate": round(judge_a_rate, 4),
        "judge_b_win_rate": round(judge_b_rate, 4),
        "b_minus_a_stream_deltas": {k: round(v, 4) for k, v in b_regressions.items()},
        "regression_tolerance_pp": REGRESSION_TOLERANCE_PP,
    }

    return DirectorVerdict(
        verdict=verdict,
        rationale="; ".join(rationale_parts) if rationale_parts else "all gates passed",
        per_task=per_task_rows,
        aggregate=aggregate_summary,
    )


# ----- verdict.md emitter -----


def render_verdict_md(
    verdict: DirectorVerdict,
    variants: dict,
    budget_tier: str,
    budget: dict,
    actual_cost_usd: float,
) -> str:
    tier = budget["tiers"][budget_tier]
    lines: List[str] = []
    lines.append(f"# Verdict — {variants['name']}")
    lines.append("")
    lines.append(f"- **A:** `{variants['a']}`")
    lines.append(f"- **B:** `{variants['b']}`")
    lines.append(f"- **Tier:** {budget_tier} (N={tier['n_tasks']})")
    lines.append(
        f"- **Budget:** target ${tier['target_usd_min']}-{tier['target_usd_max']}, "
        f"actual ${actual_cost_usd:.2f} (abort >${tier['abort_above_usd']})"
    )
    lines.append("")
    lines.append("> **Caveat.** " + tier["caveat"].strip().replace("\n", " "))
    lines.append("")
    lines.append(f"## Verdict: **{verdict.verdict.upper()}**")
    lines.append("")
    lines.append(verdict.rationale)
    lines.append("")
    lines.append("## Per-task table")
    lines.append("")
    lines.append("| task | winner | A score | B score | A SWE | B SWE | judge | reason |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in verdict.per_task:
        lines.append(
            f"| `{row['task_id']}` | {row['winner'] or 'none'} | "
            f"{row['a_score']:.3f} | {row['b_score']:.3f} | "
            f"{int(row['a_swe_bench'])} | {int(row['b_swe_bench'])} | "
            f"{row['judge_winner']} | {row['reason']} |"
        )
    lines.append("")
    agg = verdict.aggregate
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Tasks: {agg['n_tasks']} (need {agg['needed_for_majority']} for accept)")
    lines.append(f"- Wins: A={agg['a_wins']}, B={agg['b_wins']}, tie={agg['ties']}, no-winner={agg['no_winner']}")
    lines.append(f"- Veto trips: A={agg['a_veto_count']}, B={agg['b_veto_count']}")
    lines.append(
        f"- Judge win rates: A={agg['judge_a_win_rate']:.0%}, "
        f"B={agg['judge_b_win_rate']:.0%} (gate {JUDGE_WIN_THRESHOLD:.0%})"
    )
    lines.append("- Per-stream deltas (B − A, regression flag if < -20pp):")
    for k, v in agg["b_minus_a_stream_deltas"].items():
        flag = "  ← REGRESSION" if v < -REGRESSION_TOLERANCE_PP else ""
        lines.append(f"  - `{k}`: {v:+.4f}{flag}")
    lines.append("")
    lines.append("## Frozen weights")
    lines.append("")
    lines.append("```")
    for k, v in WEIGHTS.items():
        lines.append(f"{k}: {v}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)
