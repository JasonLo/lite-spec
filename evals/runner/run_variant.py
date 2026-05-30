"""Run a single (variant, task) pair.

Two modes:

  --mock-carrier (default)
      Synthesizes deterministic artifacts derived from sha256(ref + task_id)
      so the scorer + director plumbing can be exercised end-to-end without
      API spend, Docker, or a live `claude` binary. Different refs produce
      detectably different artifacts; identical refs produce identical
      artifacts (this is what enables the negative-control test).

  --no-mock-carrier (real)
      Invokes `claude -p --output-format json --print` against the wrapper
      prompt, with cwd set to a per-variant git worktree containing the
      variant's `skills/` installed into `.claude/skills/`. Trace is captured
      from stdout (stream-json events) and persisted as trace.jsonl. This
      mode is partially wired — Docker / SWE-bench runner is stubbed (see
      sandbox.py).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap
import time
from typing import Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKTREE_ROOT = REPO_ROOT / ".claude" / "worktrees"


def ensure_worktree(ref: str) -> pathlib.Path:
    """Materialize `ref` into a per-eval worktree. Reused across tasks."""
    target = WORKTREE_ROOT / f"eval-{ref.replace('/', '_')}"
    if target.exists() and (target / ".git").exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(target), ref],
        cwd=REPO_ROOT,
        check=True,
    )
    return target


def install_skills_into(worktree: pathlib.Path, sandbox: pathlib.Path) -> None:
    """Copy the worktree's `skills/` tree into the sandbox's .claude/skills.

    scripts/install.sh as it exists today downloads from GitHub by ref; for
    the runner we copy directly from the worktree to avoid network and to
    guarantee the installed skills match the ref under test."""
    src = worktree / "skills"
    dst = sandbox / ".claude" / "skills"
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


# ----- mock carrier -----


def _mock_seed(ref: str, task_id: str) -> int:
    h = hashlib.sha256(f"{ref}|{task_id}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def _mock_synth(ref: str, task: dict, run_dir: pathlib.Path) -> None:
    """Synthesize a plausible lite-spec output for (ref, task)."""
    seed = _mock_seed(ref, task["task_id"])
    quality = (seed % 1000) / 1000.0  # 0..1 deterministic per (ref, task)
    specs = run_dir / "specs"
    intent_dir = specs / "INTENT" / "I-1-mock"
    intent_dir.mkdir(parents=True, exist_ok=True)
    # Intent: always has EARS + citation; status is 'complete' only when
    # quality is high enough to credibly have passed spec-check.
    status_complete = quality >= 0.5
    verdict_passed = 1 if status_complete else 0
    verdict_total = 1 if status_complete else 0
    intent_md = textwrap.dedent(
        f"""\
        ---
        id: I-1
        title: {task['issue_title']}
        slug: mock
        status: {'complete' if status_complete else 'in_progress'}
        opened: 2026-05-24
        closed: {'2026-05-24' if status_complete else 'null'}
        superseded_by: null
        verdict_outcomes_passed: {verdict_passed}
        verdict_outcomes_total: {verdict_total}
        verdict_outcomes_passed_by_test: {verdict_passed}
        verdict_checked_at: 2026-05-24T00:00:00Z
        ---

        # Intent: {task['issue_title']}

        ## Problem

        Mock intent synthesized by run_variant.py for ref={ref}, task={task['task_id']}.

        ## Outcome

        - {task['intent_seed_outcome']} [test: pytest:{task['swe_bench_test']}::test_x]

        ## Non-Goals

        - Anything outside this issue.

        ## Constraints

        - Mock — no real implementation.

        ## Change Log

        - 2026-05-24 — Initial draft (mock).
        """
    )
    (intent_dir / "intent.md").write_text(intent_md)
    decisions_md = textwrap.dedent(
        f"""\
        # Decisions Log

        Append-only log of non-trivial decisions.

        - **D-1:** Adopted mock carrier output for task {task['task_id']} (2026-05-24). [intent: I-1]
        """
    )
    if quality < 0.2:
        # Low-quality variants drop the [intent:] tag — adherence rule will catch this.
        decisions_md = decisions_md.replace(" [intent: I-1]", "")
    (specs / "DECISIONS.md").write_text(decisions_md)

    constitution_md = textwrap.dedent(
        """\
        # Constitution: mock-project

        Ratified: 2026-05-24

        ## Artifacts

        - **P-1:** Every EARS outcome MUST carry a `[test: ...]` citation.
        - **P-2:** DECISIONS entries MUST carry an `[intent: I-N]` tag.
        - **P-3:** `status: complete` MUST be derived by spec-check, not hand-written.

        ## Amendments

        - 2026-05-24 — Initial constitution (mock).
        """
    )
    (specs / "CONSTITUTION.md").write_text(constitution_md)

    spec_check_report = textwrap.dedent(
        f"""\
        # spec-check report — 2026-05-24

        ## I-1: {task['issue_title']}  [status: {'complete' if status_complete else 'in_progress'}, {verdict_passed}/{verdict_total} outcomes passing]

        ### Code drift
        - {'[x]' if status_complete else '[ ]'} O-1: pass (test). pytest {task['swe_bench_test']} exit 0.

        ## Summary
        Intents checked: 1. Status: {'complete' if status_complete else 'in_progress'}.
        """
    )
    (run_dir / "spec_check_report.md").write_text(spec_check_report)
    (run_dir / "patch.diff").write_text(f"# mock patch for {task['task_id']} from {ref}\n")
    (run_dir / "swe_bench_result.json").write_text(
        json.dumps({"passed": status_complete, "log_tail": "mock", "error": None})
    )
    # Trace: synthesize plausible token / turn counts that scale with quality.
    base_in = 4000 + int(quality * 3000)
    base_out = 800 + int(quality * 600)
    cached = int(base_in * 0.6)
    turns = 4 + int(quality * 4)
    tool_calls = 10 + int(quality * 6)
    wall = 60.0 + quality * 90.0
    events = [
        {"type": "tokens", "input": base_in, "output": base_out, "cached_input": cached},
        *[{"type": "tool_use", "name": "Edit"} for _ in range(tool_calls)],
        {"type": "turn", "n": turns, "wall_ms": int(wall * 1000)},
        {"type": "wall_clock", "seconds": wall},
        {"type": "exit", "code": 0, "result_marker": True},
    ]
    with (run_dir / "trace.jsonl").open("w") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


# ----- real carrier -----


def parse_stream(lines: "list[str]", out_dir: pathlib.Path, fallback_wall: float) -> Tuple[int, bool, str]:
    """Normalize Claude Code `--output-format stream-json` lines into our trace.

    Pulled out of the subprocess plumbing so it can be unit-tested against
    captured real `claude` output. Writes `out_dir/trace.jsonl` and returns
    (exit_code, result_marker_seen, final_text).

    Authoritative metrics (tokens, turns, wall-clock, cost) come from the final
    `result` event, which carries cumulative totals — summing per-`assistant`
    usage would double-count. Tool calls are counted from `tool_use` content
    blocks in `assistant` messages (NOT `user` messages, which carry the
    matching tool_result blocks).
    """
    trace_path = out_dir / "trace.jsonl"
    result_marker = False
    final_text_parts: list[str] = []
    tool_uses: list[str] = []
    exit_code = 1
    result_seen = False
    tokens_ev: dict | None = None
    cost_usd: float | None = None
    turns: int | None = None
    wall_seconds: float | None = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "assistant":
            msg = ev.get("message", {})
            for block in msg.get("content", []) or []:
                bt = block.get("type")
                if bt == "text":
                    text = block.get("text", "")
                    final_text_parts.append(text)
                    if "RESULT: done" in text:
                        result_marker = True
                elif bt == "tool_use":
                    tool_uses.append(block.get("name", "?"))
        elif t == "result":
            result_seen = True
            usage = ev.get("usage") or {}
            tokens_ev = {
                "type": "tokens",
                "input": int(usage.get("input_tokens", 0)),
                "output": int(usage.get("output_tokens", 0)),
                "cached_input": int(usage.get("cache_read_input_tokens", 0)),
            }
            if ev.get("total_cost_usd") is not None:
                cost_usd = float(ev["total_cost_usd"])
            if ev.get("num_turns") is not None:
                turns = int(ev["num_turns"])
            if ev.get("duration_ms") is not None:
                wall_seconds = float(ev["duration_ms"]) / 1000.0
            exit_code = 0 if (ev.get("subtype") == "success" and not ev.get("is_error")) else 1
            final = ev.get("result")
            if isinstance(final, str):
                if final not in "".join(final_text_parts):
                    final_text_parts.append(final)
                if "RESULT: done" in final:
                    result_marker = True

    with trace_path.open("w") as f:
        f.write(json.dumps(tokens_ev or {"type": "tokens", "input": 0, "output": 0, "cached_input": 0}) + "\n")
        for name in tool_uses:
            f.write(json.dumps({"type": "tool_use", "name": name}) + "\n")
        f.write(json.dumps({"type": "turn", "n": turns if turns is not None else len(tool_uses)}) + "\n")
        f.write(json.dumps({"type": "wall_clock", "seconds": wall_seconds if wall_seconds is not None else fallback_wall}) + "\n")
        if cost_usd is not None:
            f.write(json.dumps({"type": "cost", "usd": cost_usd}) + "\n")
        f.write(json.dumps({"type": "exit", "code": exit_code if result_seen else 1, "result_marker": result_marker}) + "\n")

    final_text = "".join(final_text_parts)
    (out_dir / "final_message.txt").write_text(final_text)
    return (exit_code if result_seen else 1), result_marker, final_text


_DIFF_FENCE = re.compile(r"```(?:diff|patch)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_patch(final_text: str) -> str:
    """Pull the unified diff out of the carrier's final message.

    The prompt asks the agent to emit its code changes in a fenced ```diff```
    block. Returns the concatenated contents of every diff/patch fence (empty
    string if none), suitable to write as patch.diff for `git apply`.
    """
    blocks = [m.group(1).strip("\n") for m in _DIFF_FENCE.finditer(final_text)]
    return ("\n".join(blocks) + "\n") if blocks else ""


def _claude_print(prompt: str, cwd: pathlib.Path, out_dir: pathlib.Path) -> Tuple[int, bool, str]:
    """Invoke `claude --print --output-format stream-json` and capture trace.

    Returns (exit_code, result_marker_seen, final_text). `--verbose` is required
    by `claude` whenever `--output-format stream-json` is combined with
    `--print`. `--dangerously-skip-permissions` lets the carrier edit files
    autonomously; the harness is meant to be launched from a normal shell, not
    nested inside another Claude Code session.
    """
    if shutil.which("claude") is None:
        raise RuntimeError(
            "real-carrier mode needs the `claude` CLI on PATH; not found. "
            "Install Claude Code or run with --mock-carrier."
        )
    started = time.time()
    proc = subprocess.Popen(
        [
            "claude",
            "--print",
            "--output-format",
            "stream-json",
            "--verbose",
            "--dangerously-skip-permissions",
        ],
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None and proc.stdout is not None
    proc.stdin.write(prompt)
    proc.stdin.close()
    lines = list(proc.stdout)
    proc.wait()
    return parse_stream(lines, out_dir, fallback_wall=time.time() - started)


def _run_real(ref: str, task: dict, run_dir: pathlib.Path, skip_swe_bench: bool) -> None:
    worktree = ensure_worktree(ref)
    sandbox = run_dir / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    install_skills_into(worktree, sandbox)
    (sandbox / "specs").mkdir(exist_ok=True)
    template = (REPO_ROOT / "evals" / "runner" / "prompt_template.md").read_text()
    prompt = (
        template.replace("{{repo}}", task["repo"])
        .replace("{{issue_title}}", task["issue_title"])
        .replace("{{issue_body_excerpt}}", task["issue_body_excerpt"])
        .replace("{{intent_seed_outcome}}", task["intent_seed_outcome"])
    )
    _exit_code, _marker, final_text = _claude_print(prompt, sandbox, run_dir)
    # Copy specs/ out of the sandbox.
    sandbox_specs = sandbox / "specs"
    if sandbox_specs.exists():
        if (run_dir / "specs").exists():
            shutil.rmtree(run_dir / "specs")
        shutil.copytree(sandbox_specs, run_dir / "specs")
    # The carrier emits its code diff in a fenced ```diff``` block; persist it
    # for the (optional) SWE-bench step and for auditing.
    (run_dir / "patch.diff").write_text(extract_patch(final_text))
    # Optional SWE-bench evaluation — gracefully skipped when Docker is down or
    # --skip-swe-bench was passed. See runner/sandbox.py.
    from runner import sandbox as sb_mod  # local import for clarity
    swe = sb_mod.run_swe_bench_test(
        task, run_dir / "patch.diff", sandbox, skip=skip_swe_bench
    )
    (run_dir / "swe_bench_result.json").write_text(json.dumps(swe))


def run(
    ref: str,
    task: dict,
    run_dir: pathlib.Path,
    mock_carrier: bool,
    skip_swe_bench: bool = False,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    if mock_carrier:
        _mock_synth(ref, task, run_dir)
    else:
        _run_real(ref, task, run_dir, skip_swe_bench)


def _cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--task-json", required=True, help="JSON-encoded single task object")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--mock-carrier", action="store_true", default=True)
    ap.add_argument("--no-mock-carrier", dest="mock_carrier", action="store_false")
    ap.add_argument("--skip-swe-bench", action="store_true", default=False)
    args = ap.parse_args()
    task = json.loads(args.task_json)
    run(args.ref, task, pathlib.Path(args.run_dir), args.mock_carrier, args.skip_swe_bench)


if __name__ == "__main__":
    _cli()
