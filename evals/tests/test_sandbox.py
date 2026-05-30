"""Tests for the SWE-bench wrapper's graceful-skip behavior."""
from __future__ import annotations

import pathlib

from runner import sandbox


def test_skip_request_returns_skipped(tmp_path):
    r = sandbox.run_swe_bench_test({}, tmp_path / "patch.diff", tmp_path, skip=True)
    assert r["skipped"] is True
    assert r["passed"] is False
    assert "skip" in r["error"].lower()


def test_no_docker_returns_skipped_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "docker_available", lambda: False)
    r = sandbox.run_swe_bench_test({}, tmp_path / "patch.diff", tmp_path)
    assert r["skipped"] is True
    assert "docker" in r["error"].lower()


def test_docker_up_but_unimplemented_skips(tmp_path, monkeypatch):
    """Even with a daemon, the unimplemented runner skips rather than raising,
    so a real-carrier A/B run still completes on the other streams."""
    monkeypatch.setattr(sandbox, "docker_available", lambda: True)
    patch = tmp_path / "patch.diff"
    patch.write_text("--- a/f\n+++ b/f\n@@\n-x\n+y\n")
    r = sandbox.run_swe_bench_test({}, patch, tmp_path)
    assert r["skipped"] is True
    assert "not implemented" in r["error"].lower()


def test_docker_available_false_when_binary_missing(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda _: None)
    assert sandbox.docker_available() is False
