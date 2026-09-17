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

Current routing policy:

- `RCA_MODEL=<model>` pins all calls to one model for the single-model ablation.
- One-failure cases with one dominant telemetry candidate route cheap-first through GLM Flash, with strong GLM fallback.
- Multi-failure or ambiguous cases use the stronger GLM tier first.
- Usage is recorded per model in `usage.jsonl` for cost and wall-clock comparison.

## Evaluation To Run

Minimum comparison:

- Routed: `make dev AGENT=agents.telemetry_routed OUT=out/routed`
- Single model: `RCA_MODEL=zai-org/GLM-5.2 make dev AGENT=agents.telemetry_routed OUT=out/single-glm52`

For each run:

- `make score OUT=...`
- `make cost OUT=...`
- `python scripts/compare_runs.py --queries <dataset>/dev/query_dev.csv --out out/routed out/single-glm52 --report out/comparison.md`

Local status on 2026-09-17:

- Root command smoke-tested against a synthetic one-row no-telemetry dataset.
- Validation, cost accounting, and `scripts/compare_runs.py` all ran successfully on that smoke output.
- Full accuracy evaluation is blocked in this workspace because `data/Market-cloudbed-1`, the documented official Track 1 path, and `docs/scoring.md` are not present.

## Known Limits

The deterministic ranking can still confuse root causes with louder downstream symptoms. Trace handling uses in-window span statistics rather than a full causal graph, so packet corruption/retransmission/loss may collapse into a broader network diagnosis. Evidence text is intentionally conservative and reports uncertainty instead of inventing unsupported numbers.

Next highest-value work once the dataset is mounted:

- Run deterministic, routed, and `RCA_MODEL=zai-org/GLM-5.2` comparisons over the same 10-case slice.
- Sort misses into `candidate_missing`, `candidate_present_model_wrong`, `reason_wrong`, and `time_wrong`.
- For `candidate_missing`, extend telemetry candidate generation before prompt tuning.
- For `candidate_present_model_wrong`, tune the routed prompt and routing threshold.
- For `time_wrong`, prefer first anomalous sample over peak sample where the gold labels reward onset time.

## AI Use

Codex was used to generate the repository structure, submission entry point, telemetry agent, Dockerfile, validation helper, and draft report/README text. The team should add the exact models, assistants, prompts, and manual changes used during final development before submission.
