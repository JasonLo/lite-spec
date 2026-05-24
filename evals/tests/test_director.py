from director import director


def _ts(task_id="t", a_adh=1.0, b_adh=1.0, judge="tie", a_swe=True, b_swe=True, a_cost=0.1, b_cost=0.1, a_veto=False, b_veto=False, a_veto_ids=None, b_veto_ids=None):
    return director.TaskScores(
        task_id=task_id,
        a_adherence=a_adh,
        b_adherence=b_adh,
        judge_winner=judge,
        a_swe_bench_pass=a_swe,
        b_swe_bench_pass=b_swe,
        a_cost=a_cost,
        b_cost=b_cost,
        a_veto_tripped=a_veto,
        b_veto_tripped=b_veto,
        a_veto_ids=a_veto_ids or [],
        b_veto_ids=b_veto_ids or [],
    )


def test_identical_inputs_yield_inconclusive():
    ts = [_ts(f"t{i}", judge="tie") for i in range(5)]
    v = director.aggregate(ts)
    assert v.verdict == "inconclusive"


def test_b_wins_majority_with_judge_threshold():
    ts = [
        _ts("t1", a_adh=0.5, b_adh=1.0, judge="B", b_swe=True, a_swe=False),
        _ts("t2", a_adh=0.5, b_adh=1.0, judge="B", b_swe=True, a_swe=False),
        _ts("t3", a_adh=0.5, b_adh=1.0, judge="B", b_swe=True, a_swe=False),
        _ts("t4", a_adh=0.5, b_adh=1.0, judge="B", b_swe=True, a_swe=True),
        _ts("t5", a_adh=0.5, b_adh=1.0, judge="B", b_swe=True, a_swe=True),
    ]
    v = director.aggregate(ts)
    assert v.verdict == "accept_b"
    assert v.aggregate["b_wins"] >= v.aggregate["needed_for_majority"]


def test_b_veto_forces_reject_or_inconclusive():
    ts = [
        _ts("t1", b_veto=True, b_veto_ids=["handwritten_status_complete"]),
        _ts("t2", judge="B", b_adh=1.0, a_adh=0.5),
        _ts("t3", judge="B", b_adh=1.0, a_adh=0.5),
        _ts("t4", judge="B", b_adh=1.0, a_adh=0.5),
        _ts("t5", judge="B", b_adh=1.0, a_adh=0.5),
    ]
    v = director.aggregate(ts)
    # B has at least one veto, so even if it wins all other tasks, the accept_b
    # gate (b_vetoes == 0) is closed.
    assert v.verdict != "accept_b"
    assert v.aggregate["b_veto_count"] >= 1


def test_judge_win_rate_threshold_blocks_accept():
    # B wins all tasks on weighted score but loses judge → accept gate stays shut.
    ts = [
        _ts("t1", a_adh=0.1, b_adh=1.0, judge="A", b_swe=True),
        _ts("t2", a_adh=0.1, b_adh=1.0, judge="A", b_swe=True),
        _ts("t3", a_adh=0.1, b_adh=1.0, judge="A", b_swe=True),
        _ts("t4", a_adh=0.1, b_adh=1.0, judge="A", b_swe=True),
        _ts("t5", a_adh=0.1, b_adh=1.0, judge="A", b_swe=True),
    ]
    v = director.aggregate(ts)
    # Per-task: B has higher adherence/swe and judge=A. Whether B wins depends
    # on weighted scoring; let's just check the verdict gates.
    assert v.verdict in ("inconclusive", "reject_b")


def test_render_verdict_md_smoke():
    ts = [_ts(f"t{i}", judge="tie") for i in range(3)]
    v = director.aggregate(ts)
    md = director.render_verdict_md(
        v,
        variants={"name": "smoke", "a": "main", "b": "main"},
        budget_tier="shoestring",
        budget={
            "input_per_mtok_usd": 15,
            "output_per_mtok_usd": 75,
            "cached_input_per_mtok_usd": 1.5,
            "tiers": {
                "shoestring": {
                    "n_tasks": 3,
                    "target_usd_min": 10,
                    "target_usd_max": 20,
                    "abort_above_usd": 30,
                    "caveat": "shoestring: low N, large effects only.",
                }
            },
        },
        actual_cost_usd=12.34,
    )
    assert "# Verdict — smoke" in md
    assert "Frozen weights" in md
    assert "INCONCLUSIVE" in md
    assert "| `t0` |" in md
