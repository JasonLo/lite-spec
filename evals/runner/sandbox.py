"""SWE-bench Docker harness wrapper. STUB.

Real-carrier mode needs to:
  1. Pull the SWE-bench docker image for `task["repo"]@task["base_commit"]`.
  2. Run a container with the prepared environment.
  3. Apply the agent's patch via `git apply`.
  4. Run the named test via the repo's test runner.
  5. Return pass / fail.

This file documents that contract but does not implement it — Docker is not
available in the current dev environment. Real-carrier mode raises on the
first call until this is filled in.
"""
from __future__ import annotations

import pathlib
import shutil


def docker_available() -> bool:
    return shutil.which("docker") is not None


def run_swe_bench_test(
    task: dict, patch_path: pathlib.Path, work_dir: pathlib.Path
) -> dict:
    """Apply patch and run the cited test inside the SWE-bench sandbox.

    Returns: {"passed": bool, "log_tail": str, "error": str | None}
    """
    if not docker_available():
        return {
            "passed": False,
            "log_tail": "",
            "error": "docker not available — SWE-bench runner not wired up. "
            "This is a known stub; see evals/runner/sandbox.py.",
        }
    raise NotImplementedError(
        "SWE-bench Docker harness wrapper not implemented. See sandbox.py."
    )
