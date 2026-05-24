"""Top-level A/B runner. Loops tasks, runs A and B paired, scores all four
streams, aggregates via the director, writes verdict.md + scores.json.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import pathlib
import re
import sys
from typing import List

import yaml

# Allow running as `python -m runner.run_pair` from the evals/ dir.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EVALS_ROOT = REPO_ROOT / "evals"
sys.path.insert(0, str(EVALS_ROOT))

from director import director as director_mod  # noqa: E402
from runner import run_variant  # noqa: E402
from scorers import (  # noqa: E402
    constitution_veto,
    deterministic,
    judge as judge_mod,
    process_metrics,
)


def _load_tasks(path: pathlib.Path) -> List[dict]:
    out: List[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(json.loads(line))
    return out


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "delta"


def _score_run(run_dir: pathlib.Path, pricing: dict, swe: dict) -> dict:
    adherence = deterministic.score(run_dir)
    vetoes = constitution_veto.score(run_dir)
    metrics = process_metrics.score(run_dir, pricing)
    return {
        "adherence": adherence,
        "vetoes": vetoes,
        "metrics": metrics,
        "swe_bench": swe,
    }


def _load_swe(run_dir: pathlib.Path) -> dict:
    f = run_dir / "swe_bench_result.json"
    if not f.exists():
        return {"passed": False, "log_tail": "", "error": "no result file"}
    return json.loads(f.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", required=True, help="path to manifest.json")
    ap.add_argument("--tasks", required=True, help="path to tasks JSONL")
    ap.add_argument("--budget", choices=["shoestring", "moderate", "rigorous"], default="shoestring")
    ap.add_argument("--mock-carrier", action="store_true", default=True)
    ap.add_argument("--no-mock-carrier", dest="mock_carrier", action="store_false")
    ap.add_argument("--report-id", default=None, help="override report dir name")
    args = ap.parse_args()

    budget = yaml.safe_load((EVALS_ROOT / "budget.yaml").read_text())
    tier = budget["tiers"][args.budget]
    abort_above = float(tier["abort_above_usd"])
    pricing = {k: budget[k] for k in ("input_per_mtok_usd", "output_per_mtok_usd", "cached_input_per_mtok_usd")}

    variants = json.loads(pathlib.Path(args.variants).read_text())
    tasks = _load_tasks(pathlib.Path(args.tasks))[: tier["n_tasks"]]

    report_id = args.report_id or f"{datetime.date.today().isoformat()}-{_slugify(variants['name'])}"
    report_dir = EVALS_ROOT / "reports" / report_id
    runs_root = report_dir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    print(
        f"[run_pair] eval={report_id} tier={args.budget} N={len(tasks)} "
        f"mock_carrier={args.mock_carrier}",
        flush=True,
    )

    task_scores: List[director_mod.TaskScores] = []
    raw_scores: List[dict] = []
    running_cost = 0.0

    for task in tasks:
        for variant_key in ("a", "b"):
            ref = variants[variant_key]
            run_dir = runs_root / f"{task['task_id']}-{variant_key}"
            print(f"[run_pair] running ref={ref} task={task['task_id']} variant={variant_key} ...", flush=True)
            run_variant.run(ref, task, run_dir, args.mock_carrier)

        a_dir = runs_root / f"{task['task_id']}-a"
        b_dir = runs_root / f"{task['task_id']}-b"
        a_scores = _score_run(a_dir, pricing, _load_swe(a_dir))
        b_scores = _score_run(b_dir, pricing, _load_swe(b_dir))
        judge_result = judge_mod.score(a_dir, b_dir)
        a_cost = float(a_scores["metrics"]["cost_usd"])
        b_cost = float(b_scores["metrics"]["cost_usd"])
        running_cost += a_cost + b_cost
        # Judge winner per task = majority across rubric dims (ties → tie).
        if judge_result["a_wins"] > judge_result["b_wins"]:
            judge_winner = "A"
        elif judge_result["b_wins"] > judge_result["a_wins"]:
            judge_winner = "B"
        else:
            judge_winner = "tie"
        ts = director_mod.TaskScores(
            task_id=task["task_id"],
            a_adherence=a_scores["adherence"]["pass_rate"],
            b_adherence=b_scores["adherence"]["pass_rate"],
            judge_winner=judge_winner,
            a_swe_bench_pass=bool(a_scores["swe_bench"].get("passed")),
            b_swe_bench_pass=bool(b_scores["swe_bench"].get("passed")),
            a_cost=a_cost,
            b_cost=b_cost,
            a_veto_tripped=a_scores["vetoes"]["any_tripped"],
            b_veto_tripped=b_scores["vetoes"]["any_tripped"],
            a_veto_ids=a_scores["vetoes"]["tripped_ids"],
            b_veto_ids=b_scores["vetoes"]["tripped_ids"],
        )
        task_scores.append(ts)
        raw_scores.append(
            {
                "task_id": task["task_id"],
                "a": a_scores,
                "b": b_scores,
                "judge": judge_result,
            }
        )
        print(
            f"[run_pair]   adherence A={a_scores['adherence']['pass_rate']:.2f} "
            f"B={b_scores['adherence']['pass_rate']:.2f}  "
            f"vetoes A={a_scores['vetoes']['tripped_ids']} B={b_scores['vetoes']['tripped_ids']}  "
            f"judge_winner={judge_winner}  cost ${a_cost+b_cost:.3f}  running ${running_cost:.2f}",
            flush=True,
        )
        if running_cost > abort_above:
            print(
                f"[run_pair] ABORT: running cost ${running_cost:.2f} > tier abort threshold ${abort_above}",
                file=sys.stderr,
            )
            break

    verdict = director_mod.aggregate(task_scores)
    (report_dir / "scores.json").write_text(
        json.dumps(
            {
                "report_id": report_id,
                "variants": variants,
                "budget_tier": args.budget,
                "actual_cost_usd": round(running_cost, 4),
                "verdict": dataclasses.asdict(verdict),
                "raw": raw_scores,
            },
            indent=2,
        )
    )
    (report_dir / "verdict.md").write_text(
        director_mod.render_verdict_md(verdict, variants, args.budget, budget, running_cost)
    )
    print(f"[run_pair] verdict: {verdict.verdict}  rationale: {verdict.rationale}", flush=True)
    print(f"[run_pair] report: {report_dir / 'verdict.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
