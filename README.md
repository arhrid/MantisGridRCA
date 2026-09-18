# MantisGrid RCA

Track 1 submission for the MantisGrid Hackathon 2026: Infrastructure Root Cause Analysis.

The project runs headless over the `Market-cloudbed-1` bundle and writes:

- `predictions.csv`
- `evidence/<row_id>.md`
- `usage.jsonl`

## Expected Output

The submission must write all outputs under the `--out` directory passed to `run.py`.

```text
<out>/
  predictions.csv
  usage.jsonl
  evidence/
    <row_id>.md
```

`predictions.csv` contains one row per query. The important columns are:

- `row_id`
- `prediction`
- `task_index`
- `wall_s`
- `prompt_tokens`
- `completion_tokens`
- `calls`

The `prediction` field is a fenced JSON object. The evaluator expects answer keys in this order:

1. `root cause occurrence datetime`
2. `root cause component`
3. `root cause reason`

Use `format_prediction()` in `run.py` so the key order stays valid. The agent may omit fields that were not requested by the query, but it must emit exactly the requested number of failure objects.

Each `evidence/<row_id>.md` file should explain the answer for human review. Our evidence files use:

- `## Answer`
- `## Confidence`
- `## Evidence`
- `## Ruled out`
- `## Limitations`
- `## Model usage` when model calls are made

`usage.jsonl` records per-case wall time and token usage by model. This supports cost and time comparisons.

## Official Sources

The official hackathon repo may be cloned separately at:

```text
/Users/benchong/Work/Hackathon/hackathon-2026-official
```

Track 1 source materials, starter code, and local data live under:

```text
/Users/benchong/Work/Hackathon/hackathon-2026-official/track-1
```

## Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run two dev cases:

```bash
make validate DATASET=data/Market-cloudbed-1
```

Run the full dev split:

```bash
make dev DATASET=data/Market-cloudbed-1 OUT=out/routed
make score DATASET=data/Market-cloudbed-1 OUT=out/routed
make cost OUT=out/routed
```

Optional Featherless/GLM refinement:

```bash
export FEATHERLESS_API_KEY=<your key>
make dev DATASET=data/Market-cloudbed-1 OUT=out/routed
RCA_MODEL=zai-org/GLM-5.2 make dev DATASET=data/Market-cloudbed-1 OUT=out/single-glm52
make compare DATASET=data/Market-cloudbed-1 OUT=out/routed
python scripts/compare_runs.py \
  --queries data/Market-cloudbed-1/dev/query_dev.csv \
  --out out/routed out/single-glm52 \
  --report out/comparison.md
```

The agent reads `FEATHERLESS_BASE_URL` when set and otherwise uses `https://api.featherless.ai/v1`. No key or endpoint is hard-coded.
Without `RCA_MODEL`, the agent routes one dominant-candidate cases cheap-first through GLM Flash models and uses stronger GLM models for ambiguous or multi-failure cases. Setting `RCA_MODEL` pins every LLM call to a single model for the required ablation.

## Official Starter Local Run

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
OFFICIAL_TRACK1_DIR=/path/to/hackathon-2026-official/track-1 LIMIT=2 scripts/run_official_local.sh
LIMIT=10 AGENT=agents.heuristic scripts/run_official_local.sh
LIMIT=10 AGENT=agents.routed scripts/run_official_local.sh
OUT=/tmp/rca-out LIMIT=2 scripts/run_official_local.sh
```

By default, outputs go to:

```text
/Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/out/local-dev/
```

Do not commit the Featherless API key. Export it only in your shell.

## Judge Command

The repository intentionally has one Dockerfile, at the root. It supports the required command shape:

```bash
docker build -t your-team .
docker run --rm \
  -e FEATHERLESS_API_KEY=<key> \
  -v <bundle>:/data:ro \
  -v <empty-folder>:/out \
  your-team \
  python run.py --dataset /data --queries /data/query.csv --out /out
```

## Submission Repository

Judges should evaluate the public repository's default branch at the latest pushed commit when cloned. The work intended for judging is merged to `main`.

Secrets are not committed. API keys are supplied only through environment variables such as `FEATHERLESS_API_KEY`; local files such as `.env`, `.env.local`, and `.env.local.save` are ignored by Git.

## Agent

Default agent: `starter.agents.mantis`.

It parses the window and failure count from each instruction, builds bounded candidates from metrics, logs, and traces, and emits a best guess even when telemetry or model calls are inconclusive. Evidence files include the selected answer, confidence, telemetry facts used, and nearby candidates ruled out.
Model calls receive only compact candidate summaries. The Featherless client retries transient provider failures, falls back across the configured model tier, strips model thinking blocks, and records per-model token usage for `cost.py` and `scripts/compare_runs.py`.

## AI Tool Disclosure

AI systems used during development:

- OpenAI Codex coding agent: generated and edited code, scripts, and documentation under human direction.
- Featherless-hosted GLM family models: used by the submitted RCA agent at runtime when `FEATHERLESS_API_KEY` is available.
- GLM Flash models: used by the default routed policy for low-ambiguity, dominant-candidate cases.
- Stronger GLM models, currently `zai-org/GLM-5.2` and `zai-org/GLM-5.1`: used by the default routed policy for ambiguous or multi-failure cases. `RCA_MODEL=<model>` pins every model call to one GLM model for single-model comparison.

Agent frameworks and orchestration:

- No external agent framework is used.
- The agent is a local Python orchestration module, `agents.telemetry_routed`, called by `run.py`.
- The model client uses the OpenAI-compatible Python SDK against `FEATHERLESS_BASE_URL`, defaulting to `https://api.featherless.ai/v1`.

AI-generated or AI-assisted work:

- Root submission shape: `Dockerfile`, `run.py`, and command-line wiring.
- RCA logic in `agents.telemetry_routed`: telemetry loading, candidate generation, model routing, fallback behavior, and evidence formatting.
- Featherless/OpenAI-compatible client in `llm.py`.
- Local validation, scoring, cost, and comparison scripts.
- README, REPORT, and evaluation documentation drafts.

Team-authored and team-owned work:

- Project goals, track selection, and final implementation direction.
- Local credentials and API-key handling.
- Review and acceptance of generated changes.
- Evaluation runs and interpretation of results.
- Final repository contents and submission decisions.

## Docs

- `REPORT.md`
- `eval/README.md`
- `docs/mantisgrid-track1-rca-por.md`
- `docs/mantisgrid-hackathon-implementation-plan.md`
- `docs/mantisgrid-codex-hackathon-guidelines.md`
