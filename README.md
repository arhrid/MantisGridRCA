# MantisGrid RCA

Barebones project repository for the MantisGrid Hackathon Track 1: Root Cause Analysis.

## Goal

Build an accurate and efficient RCA system that investigates cluster incidents using telemetry evidence and produces a root-cause hypothesis with supporting evidence.

The project is currently in planning mode because the hackathon dataset, API details, and final access instructions are not available yet.

## Expected Inputs

- Incident definitions
- Gold labels for evaluation
- Metrics
- Logs
- Traces
- Cluster, node, workload, service, pod, job, GPU, accelerator, or resource metadata where available

## Planned Shape

- Python RCA backend and workflow orchestrator
- Direct MantisGrid API client as the default data path
- Optional MCP adapter if final instructions require or favor it
- Provider-independent LLM interface
- Constrained telemetry tools owned by the backend
- Structured investigation traces
- Evaluation harness for labeled incidents
- Streamlit UI for local review and demos
- Docker-based local runtime

## Initial RCA Flow

1. Load incident context.
2. Identify affected entities and symptoms.
3. Generate candidate root-cause hypotheses.
4. Request bounded telemetry evidence through backend tools.
5. Update hypotheses based on evidence.
6. Produce a final RCA answer with confidence, evidence, blast radius, and next action.

## Current Status

- Repository initialized
- Planning documents are in `docs/`
- Dataset and API access are pending
- Implementation has not started

## Next Steps

1. Confirm final hackathon instructions, dataset format, API access, credentials, and judging criteria.
2. Add a minimal Dockerized Python project skeleton.
3. Implement an incident loader and data access stub.
4. Add canonical RCA state and trace logging.
5. Build a first end-to-end RCA workflow over one sample incident once data is available.

## Docs

- `docs/mantisgrid-track1-rca-por.md`
- `docs/mantisgrid-hackathon-implementation-plan.md`
- `docs/mantisgrid-codex-hackathon-guidelines.md`
