# MantisGrid RCA

Barebones project repository for the MantisGrid Hackathon Track 1: Infrastructure Root Cause Analysis.

## Goal

Build an accurate and efficient RCA system that investigates cluster incidents using telemetry evidence and produces a root-cause hypothesis with supporting evidence.

The official hackathon repo is cloned separately at:

```text
/Users/benchong/Work/Hackathon/hackathon-2026-official
```

Track 1 source materials, starter code, and local data live under:

```text
/Users/benchong/Work/Hackathon/hackathon-2026-official/track-1
```

## Expected Inputs

- Incident definitions
- 70 labeled cases for evaluation
- 12 GB of real telemetry
- Metrics
- Logs
- Traces
- Cluster, node, workload, service, pod, job, GPU, accelerator, or resource metadata where available
- 7 GLM models on a provided Featherless key, subject to final credential details

## Planned Shape

- Python RCA backend and workflow orchestrator
- Query-based telemetry access; raw telemetry should not be pasted into model context
- File-backed telemetry access over the official Track 1 bundle
- Provider-independent LLM interface
- Routed model selection plus a single-model baseline
- Constrained telemetry tools owned by the backend
- Structured investigation traces
- Evaluation harness for labeled incidents
- Optional local review/demo tooling
- Local Python runtime for development
- Root-level Docker submission path for judging

## Initial RCA Flow

1. Load incident context.
2. Identify affected entities and symptoms.
3. Generate candidate root-cause hypotheses.
4. Request bounded telemetry evidence through backend tools.
5. Update hypotheses based on evidence.
6. Produce a final RCA answer with time, component, cause, confidence, evidence, blast radius, and next action.
7. Benchmark routed model use against a single-model baseline.

## Current Status

- Repository initialized
- Planning documents are in `docs/`
- Local run helper is available at `scripts/run_official_local.sh`
- The official starter/data are referenced from the separate official checkout
- Implementation of the real agent has not started

## Local Run

From this repo:

```bash
cd /Users/benchong/Work/Hackathon/MantisGridRCA
```

Run 2 cases with the free heuristic baseline:

```bash
LIMIT=2 scripts/run_official_local.sh
```

Run 2 cases with the routed GLM starter:

```bash
export FEATHERLESS_API_KEY='your-key-here'
LIMIT=2 AGENT=agents.routed scripts/run_official_local.sh
```

Run all 70 dev cases:

```bash
scripts/run_official_local.sh
```

Useful options:

```bash
LIMIT=10 AGENT=agents.heuristic scripts/run_official_local.sh
LIMIT=10 AGENT=agents.routed scripts/run_official_local.sh
OUT=/tmp/rca-out LIMIT=2 scripts/run_official_local.sh
```

By default, outputs go to:

```text
/Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/out/local-dev/
```

Do not commit the Featherless API key. Export it only in your shell.

## Next Steps

1. Keep the official `run.py` contract intact.
2. Build one simple real agent module to replace the starter heuristic.
3. Add telemetry summarization over metrics, traces, and targeted logs.
4. Compare routed GLM use against a single-model baseline.
5. Improve evidence quality and uncertainty reporting.

## Docs

- `docs/mantisgrid-track1-rca-por.md`
- `docs/mantisgrid-hackathon-implementation-plan.md`
- `docs/mantisgrid-codex-hackathon-guidelines.md`
