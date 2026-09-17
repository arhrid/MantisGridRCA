# MantisGridRCA Report

## Track

Track 1: Root Cause Analysis.

## Agent

`agents.telemetry_routed` parses the incident window and failure count, reads telemetry only from the mounted dataset, and writes `predictions.csv` plus `evidence/<row_id>.md`.

The agent first builds deterministic candidates from:

- metric anomalies across container, node, service, and mesh CSV files;
- trace span latency and non-OK status within the incident window;
- service/proxy log entries that indicate process termination, timeout, or errors.

When `FEATHERLESS_API_KEY` is available, a single GLM reasoning call refines the ranked candidates. Calls use `FEATHERLESS_BASE_URL` when present and fall back across the GLM family. If the model path fails or no key is set, the deterministic answer is still emitted.

## Evaluation To Run

Minimum comparison:

- Routed: `make dev AGENT=agents.telemetry_routed OUT=out/routed`
- Single model: `RCA_MODEL=zai-org/GLM-5.2 make dev AGENT=agents.telemetry_routed OUT=out/single-glm52`

For each run:

- `make score OUT=...`
- `make cost OUT=...`

## Known Limits

The deterministic ranking can still confuse root causes with louder downstream symptoms. Trace handling uses in-window span statistics rather than a full causal graph, so packet corruption/retransmission/loss may collapse into a broader network diagnosis. Evidence text is intentionally conservative and reports uncertainty instead of inventing unsupported numbers.

## AI Use

Codex was used to generate the repository structure, submission entry point, telemetry agent, Dockerfile, validation helper, and draft report/README text. The team should add the exact models, assistants, prompts, and manual changes used during final development before submission.
