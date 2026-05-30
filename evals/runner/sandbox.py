"""SWE-bench Docker harness wrapper.

Real SWE-bench execution needs a running Docker daemon and the per-repo
SWE-bench images; it:
  1. Pulls the SWE-bench image for `task["repo"]@task["base_commit"]`.
  2. Runs a container with the prepared environment.
  3. Applies the agent's patch via `git apply`.
  4. Runs the named test via the repo's test runner.
  5. Returns pass / fail.

That contract is documented here but **not implemented** — it requires a Docker
daemon plus SWE-bench dataset images that are not assumed to be present. So this
wrapper degrades gracefully: when Docker is unavailable (or the SWE-bench step
is skipped), it returns a `skipped` result instead of raising. A skipped result
contributes neutrally to the director (both variants score 0 on the swe_bench
stream, so the comparison is unaffected) — which is exactly what we want when
A/B testing a *spec-workflow* feature, where the signal lives in the other three
evidence streams.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess


def docker_available() -> bool:
    """True only if the Docker *daemon* is reachable, not just the binary.

    `shutil.which("docker")` is truthy whenever the CLI is installed even if the
    daemon is down (common on WSL2 when Docker Desktop isn't running), so we
    actually ping the daemon with `docker info`."""
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0


def skipped_result(reason: str) -> dict:
    return {"passed": False, "skipped": True, "log_tail": "", "error": reason}


def run_swe_bench_test(
    task: dict,
    patch_path: pathlib.Path,
    work_dir: pathlib.Path,
    *,
    skip: bool = False,
) -> dict:
    """Apply patch and run the cited test inside the SWE-bench sandbox.

    Returns: {"passed": bool, "skipped": bool, "log_tail": str, "error": str|None}

    Skips (never raises) when explicitly requested, when Docker is unavailable,
    or when the patch is missing. The real Docker harness is intentionally not
    implemented here — see the module docstring.
    """
    if skip:
        return skipped_result("SWE-bench skipped by request (--skip-swe-bench).")
    if not docker_available():
        return skipped_result(
            "Docker daemon not reachable — SWE-bench skipped. Start Docker and "
            "drop --skip-swe-bench to enable the code-pass stream."
        )
    if not patch_path.exists() or not patch_path.read_text().strip():
        return skipped_result("no patch.diff emitted by the carrier — nothing to apply.")
    # Docker is available but the SWE-bench image/runner integration is not
    # implemented in this harness. Degrade to skipped rather than raising so a
    # real-carrier A/B run still completes on the other three evidence streams.
    return skipped_result(
        "SWE-bench Docker runner not implemented in this harness "
        "(images + container orchestration are out of scope); skipping."
    )
