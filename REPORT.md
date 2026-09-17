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

Submission readiness:

- The only Dockerfile in the repository is the root `Dockerfile`.
- `run.py` keeps the required command-line shape: `python run.py --dataset /data --queries /data/query.csv --out /out`.
- The default agent is `agents.telemetry_routed`, so the judge command does not need an extra `--agent`.
- The agent reads the model key from `FEATHERLESS_API_KEY` and the endpoint from `FEATHERLESS_BASE_URL` when set.
- `scripts/validate_submission.py` checks prediction count, JSON shape, key order, and the four required evidence sections.

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

AI systems used during development:

- OpenAI Codex coding agent generated and edited the submission entry point, Docker packaging, telemetry RCA agent, Featherless client, validation/comparison harnesses, and documentation drafts under human direction.
- Featherless-hosted GLM family models are used by the submitted agent at runtime when `FEATHERLESS_API_KEY` is available. The default routed policy uses GLM Flash models for dominant one-candidate cases and stronger GLM models for ambiguous or multi-failure cases. `RCA_MODEL=<model>` pins the agent to one GLM model for ablation.

The team wrote the project goals, reviewed generated changes, supplied credentials locally, ran evaluations, and owns final submission decisions. No API keys or secrets are committed.
