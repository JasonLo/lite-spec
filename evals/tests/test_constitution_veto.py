from scorers import constitution_veto


def test_good_run_no_vetoes(good_run):
    result = constitution_veto.score(good_run)
    assert result["any_tripped"] is False
    assert result["tripped_ids"] == []


def test_handwritten_complete_trips_veto(handwritten_complete_run):
    result = constitution_veto.score(handwritten_complete_run)
    assert "handwritten_status_complete" in result["tripped_ids"]


def test_no_outcome_trips_veto(no_outcome_run):
    result = constitution_veto.score(no_outcome_run)
    assert "intent_missing_outcome_section" in result["tripped_ids"]


def test_empty_constitution_trips_veto(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "CONSTITUTION.md").write_text("# Constitution: empty\n\n(no principles)\n")
    result = constitution_veto.score(tmp_path)
    assert "constitution_present_but_empty" in result["tripped_ids"]


def test_decisions_duplicate_id_trips_veto(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "DECISIONS.md").write_text(
        "# Decisions\n\n- **D-1:** First. [intent: I-1]\n- **D-1:** Mutated. [intent: I-1]\n"
    )
    result = constitution_veto.score(tmp_path)
    assert "decisions_mutated_in_place" in result["tripped_ids"]
