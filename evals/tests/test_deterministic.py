from scorers import deterministic


def test_good_run_passes_all_rules(good_run):
    result = deterministic.score(good_run)
    assert result["pass_count"] == result["total"], result["rules"]
    assert result["pass_rate"] == 1.0


def test_handwritten_complete_is_caught(handwritten_complete_run):
    result = deterministic.score(handwritten_complete_run)
    rule = next(r for r in result["rules"] if r["rule_id"] == "status_derived_not_handwritten")
    assert rule["passed"] is False
    assert "complete" in rule["evidence"]


def test_untagged_decisions_caught(untagged_decisions_run):
    result = deterministic.score(untagged_decisions_run)
    rule = next(r for r in result["rules"] if r["rule_id"] == "decisions_tagged")
    assert rule["passed"] is False


def test_missing_artifacts_flagged(tmp_path):
    # Empty run dir — most rules should fail.
    (tmp_path / "specs").mkdir()
    result = deterministic.score(tmp_path)
    assert result["pass_rate"] < 0.5
    rule = next(r for r in result["rules"] if r["rule_id"] == "intent_exists")
    assert rule["passed"] is False
