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
python -m runner.run_pair \
  --variants variants/manifest.example.json \
  --tasks tasks/swe-bench-lite-subset.jsonl \
  --budget shoestring \
  --mock-carrier
```

The `--mock-carrier` flag synthesizes deterministic per-variant outputs so the
plumbing can be smoke-tested without API spend or Docker. Drop it (and provide
real refs) once the carrier-task runner is wired to `claude -p`.

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

## Mock carrier vs real carrier

The default `--mock-carrier` mode synthesizes per-variant artifacts from a seed
derived from the variant ref, so the four scorers and the director can be
exercised end-to-end without API cost.

The real-carrier mode (`--no-mock-carrier`) is wired but currently expects
`claude` to be on PATH and a SWE-bench Docker harness to be available — see
`runner/sandbox.py` for the unfinished hook. Real-carrier mode is **not
smoke-tested in this pass** and should be considered a stub until Docker is
available.
