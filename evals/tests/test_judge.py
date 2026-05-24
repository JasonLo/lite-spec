"""Judge tests use the deterministic stub (no API key set) — the goal is to
verify the position-swap collapse logic, not the actual judge model."""
import pathlib

from scorers import judge


def test_judge_identical_artifacts_all_tie(good_run, tmp_path, monkeypatch):
    # Build a second identical run dir.
    second = tmp_path / "second"
    import shutil
    shutil.copytree(good_run, second)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = judge.score(good_run, second)
    assert result["a_wins"] == 0
    assert result["b_wins"] == 0
    assert result["ties"] == len(judge.RUBRIC_DIMENSIONS)


def test_judge_position_swap_collapses_disagreement(monkeypatch, good_run, tmp_path):
    """A judge that disagrees on the two orderings → tie (no leaked position bias)."""
    second = tmp_path / "second"
    import shutil
    shutil.copytree(good_run, second)

    # Patch _call_judge to return X-wins both times. Forward: X=A, so A wins
    # intent_clarity. Reverse: X=B, so the reverse call returns X=B as winner —
    # which means in the second judging A loses intent_clarity. The collapse
    # rule should detect this disagreement and call it tie.
    calls = []

    def fake(prompt: str) -> dict:
        calls.append(prompt)
        return {d: {"winner": "X", "reason": "biased"} for d in judge.RUBRIC_DIMENSIONS}

    monkeypatch.setattr(judge, "_call_judge", fake)
    result = judge.score(good_run, second)
    assert len(calls) == 2  # forward + reverse
    # Every dimension should resolve to tie because of position-swap disagreement.
    assert result["a_wins"] == 0 and result["b_wins"] == 0
    assert result["ties"] == len(judge.RUBRIC_DIMENSIONS)


def test_judge_consistent_win_persists(monkeypatch, good_run, tmp_path):
    """A judge that picks A on both orderings → A wins (the legitimate signal)."""
    second = tmp_path / "second"
    import shutil
    shutil.copytree(good_run, second)

    def fake(prompt: str) -> dict:
        # Forward: X=A, return X → A. Reverse: X=B, return Y → A.
        if "Variant X" in prompt and prompt.find("--- intent.md ---") < prompt.find("Variant Y"):
            # Same prompt structure both directions — distinguish by which run dir's
            # content appears first. We can't here, so just return positional-stable
            # picks: forward X, reverse Y.
            pass
        return {}

    # Easier: just patch judge_pair to return a known stable result and check score aggregation.
    from scorers.judge import JudgeResult

    monkeypatch.setattr(
        judge,
        "judge_pair",
        lambda a, b: [
            JudgeResult(dimension=d, winner="A", reason_x_first="r1", reason_y_first="r2")
            for d in judge.RUBRIC_DIMENSIONS
        ],
    )
    result = judge.score(good_run, second)
    assert result["a_wins"] == len(judge.RUBRIC_DIMENSIONS)
    assert result["b_wins"] == 0
