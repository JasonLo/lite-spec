from scorers import process_metrics


def test_metrics_aggregated(good_run, pricing):
    m = process_metrics.score(good_run, pricing)
    assert m["input_tokens"] == 5000
    assert m["output_tokens"] == 1000
    assert m["cached_input_tokens"] == 3000
    assert m["tool_calls"] == 8
    assert m["turns"] == 5
    assert m["wall_clock_seconds"] == 120.0
    assert m["exit_code"] == 0
    assert m["result_marker_seen"] is True
    # cost: fresh_input = 2000 * 15/1e6 = 0.03; cached = 3000 * 1.5/1e6 = 0.0045; output = 1000 * 75/1e6 = 0.075
    assert abs(m["cost_usd"] - (0.03 + 0.0045 + 0.075)) < 1e-6


def test_missing_trace_returns_zeros(tmp_path, pricing):
    m = process_metrics.score(tmp_path, pricing)
    assert m["input_tokens"] == 0
    assert m["cost_usd"] == 0.0


def test_reported_cost_event_overrides_token_estimate(tmp_path, pricing):
    import json
    # Tokens would estimate ~0.03, but an explicit cost event must win verbatim.
    (tmp_path / "trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"type": "tokens", "input": 1000, "output": 200, "cached_input": 0}),
                json.dumps({"type": "cost", "usd": 0.4242}),
                json.dumps({"type": "exit", "code": 0, "result_marker": True}),
            ]
        )
    )
    m = process_metrics.score(tmp_path, pricing)
    assert m["cost_usd"] == 0.4242


def test_cost_handles_no_cached_field(tmp_path, pricing):
    import json
    (tmp_path / "trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"type": "tokens", "input": 1000, "output": 200}),
                json.dumps({"type": "exit", "code": 0, "result_marker": False}),
            ]
        )
    )
    m = process_metrics.score(tmp_path, pricing)
    # fresh_input=1000, output=200 → 1000*15/1e6 + 200*75/1e6 = 0.015 + 0.015 = 0.03
    assert abs(m["cost_usd"] - 0.030) < 1e-6
