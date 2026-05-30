# lite-spec evaluation harness

A/B evaluation harness for the `lite-spec` plugin. Given two git refs (variant A
and variant B), runs each against a fixed task set, collects four evidence
streams per run, and produces a director verdict.

This is a **pilot**, not a powered study. The shoestring tier reliably detects
deltas with ≥15–20pp effect on the weighted score; smaller deltas are not
distinguishable from noise.

## Layout

```
evals/
├── tasks/                              carrier task definitions (JSONL)
├── variants/manifest.example.json      two git refs to compare
├── runner/                             orchestration + per-variant execution
├── scorers/                            four evidence streams
├── director/                           deterministic aggregator + verdict.md
├── reports/<eval-id>/                  per-run traces + scores + verdict
├── tests/                              pytest for scorers + director
├── budget.yaml                         tier definitions (shoestring/moderate/rigorous)
└── pyproject.toml
```

## Quick start

```bash
cd evals/

# smoke-test the plumbing (no API spend, no Docker):
uv run python -m runner.run_pair \
  --variants variants/manifest.example.json \
  --tasks tasks/swe-bench-lite-subset.jsonl \
  --budget shoestring --mock-carrier

# tests (dev extra adds pytest into the same venv as PyYAML):
uv run --extra dev pytest -q
```

The `--mock-carrier` flag synthesizes deterministic per-variant outputs so the
plumbing can be exercised without API spend, Docker, or a live `claude` binary.

## A/B testing a real feature

Point the manifest at the two refs you want to compare (e.g. `main` vs a branch
that changes a `spec-` skill), then run the real carrier:

```bash
uv run python -m runner.run_pair \
  --variants variants/my-delta.json \
  --tasks tasks/swe-bench-lite-subset.jsonl \
  --budget shoestring --no-mock-carrier
```

Real-carrier mode requires the `claude` CLI on PATH. For each (variant, task)
it materializes the ref into a git worktree, copies that ref's `skills/` tree
into a sandbox `.claude/skills/`, runs `claude --print --output-format
stream-json --verbose --dangerously-skip-permissions` against the carrier
prompt, and captures the resulting `specs/` tree + trace. **Launch it from a
normal shell, not nested inside another Claude Code session** — the autonomous
`--dangerously-skip-permissions` carrier is what spends the budget.

## Evidence streams

1. **Deterministic spec-adherence** (`scorers/deterministic.py`) — binary rules
   against captured artifacts (intent.md EARS form, `[intent:]` tags on
   decisions, frontmatter validity, no hand-written `status: complete`).
2. **LLM-as-judge pairwise** (`scorers/judge.py`) — Opus pairwise rubric scoring;
   each pair is judged twice with positions swapped; a variant only wins a
   rubric dimension if it wins both orderings. Otherwise the dimension is a tie.
3. **Process / cost metrics** (`scorers/process_metrics.py`) — input/output
   tokens, tool calls, turns, wall-clock, and $ cost parsed from the runner
   trace.
4. **Constitution hard-veto** (`scorers/constitution_veto.py`) — any veto trip
   causes that variant to lose that task automatically.

## Director

`director/director.py` is deterministic, not another LLM. Per-task weighted
score:

```
score = 0.4*adherence + 0.3*judge_win + 0.2*swe_bench_pass + 0.1*cost_score
```

Weights are frozen in code. Any change to them is itself a methodology change
and must land in a separate PR from a delta evaluation.

B is accepted iff: it wins on a majority of tasks AND no hard-vetos AND
judge-win rate ≥ 60% AND no stream regresses by >20%. Otherwise reject (or
inconclusive on tie).

## SWE-bench stream (optional)

The `swe_bench_pass` stream (0.2 weight) needs a running Docker daemon and the
SWE-bench images to actually apply the carrier's patch and run the cited test.
When no daemon is reachable, the runner **auto-skips** this stream and prints a
notice; you can also force it off with `--skip-swe-bench`. A skipped stream
contributes neutrally — both variants score 0 on `swe_bench`, so the comparison
is decided by the other three streams (adherence, judge, process metrics, and
the constitution veto). That is the right mode for A/B testing a *spec-workflow*
feature, where the signal lives in the spec artifacts rather than the code patch.

The Docker harness itself (image pull + container orchestration) is documented
but not implemented in `runner/sandbox.py`; it degrades to a `skipped` result
rather than raising, so a real-carrier run always completes.

## Mock carrier vs real carrier

The default `--mock-carrier` mode synthesizes per-variant artifacts from a seed
derived from the variant ref, so the four scorers and the director can be
exercised end-to-end without API cost. Identical refs produce identical
artifacts — the negative control (`a == b` ⇒ `inconclusive`).

The real-carrier mode (`--no-mock-carrier`) drives `claude` per the carrier
prompt and is validated end-to-end with the subprocess stubbed (see
`tests/test_run_pair.py`); its stream parser is checked against a captured real
`claude` trace (`tests/fixtures/claude_stream_real.jsonl`).
