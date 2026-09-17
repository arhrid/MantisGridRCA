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
```

The agent reads `FEATHERLESS_BASE_URL` when set and otherwise uses `https://api.featherless.ai/v1`. No key or endpoint is hard-coded.

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

The root `Dockerfile` supports the required command shape:

```bash
docker build -t your-team .
docker run --rm \
  -e FEATHERLESS_API_KEY=<key> \
  -v <bundle>:/data:ro \
  -v <empty-folder>:/out \
  your-team \
  python run.py --dataset /data --queries /data/query.csv --out /out
```

## Agent

Default agent: `starter.agents.mantis`.

It parses the window and failure count from each instruction, builds bounded candidates from telemetry summaries, uses query-aware output shaping, and emits a best guess even when model calls are inconclusive. Evidence files include the selected answer, confidence, telemetry facts used, nearby candidates ruled out, limitations, and model usage where applicable.

## AI Tool Disclosure

Codex was used to generate the submission structure, Dockerfile, `run.py`, telemetry agent, validation helper, and draft documentation. The team should update this section before submission with every AI model, coding assistant, and agent framework used during final development, plus what was AI-generated versus manually written.

## Docs

- `REPORT.md`
- `eval/README.md`
- `docs/mantisgrid-track1-rca-por.md`
- `docs/mantisgrid-hackathon-implementation-plan.md`
- `docs/mantisgrid-codex-hackathon-guidelines.md`
