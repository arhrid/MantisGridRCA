# MantisGrid RCA

Barebones project repository for the MantisGrid Hackathon Track 1: Infrastructure Root Cause Analysis.

## Goal

Build an accurate and efficient RCA system that investigates cluster incidents using telemetry evidence and produces a root-cause hypothesis with supporting evidence.

The project is currently in planning mode. The challenge slide describes the dataset and model pool, but the dataset, starter pack, credentials, API details, and final access instructions are not present in this checkout yet.

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
- Direct MantisGrid API client or MCP adapter, depending on final instructions
- Provider-independent LLM interface
- Routed model selection plus a single-model baseline
- Constrained telemetry tools owned by the backend
- Structured investigation traces
- Evaluation harness for labeled incidents
- Streamlit UI for local review and demos
- Local Python runtime, with Docker packaging only if final instructions require it

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
- Dataset, starter pack, credentials, and API access are pending in this checkout
- Implementation has not started

## Next Steps

1. Confirm final hackathon instructions, dataset format, starter pack, API/MCP access, Featherless credentials, and judging criteria.
2. Add a minimal local Python project skeleton.
3. Implement an incident loader and data access stub.
4. Add canonical RCA state and trace logging.
5. Add routed-vs-single-model benchmark plumbing.
6. Build a first end-to-end RCA workflow over one sample incident once data is available.

## Docs

- `docs/mantisgrid-track1-rca-por.md`
- `docs/mantisgrid-hackathon-implementation-plan.md`
- `docs/mantisgrid-codex-hackathon-guidelines.md`
