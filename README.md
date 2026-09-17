# MantisGrid RCA

Track 1 submission for the MantisGrid Hackathon 2026: Infrastructure Root Cause Analysis.

The project runs headless over the `Market-cloudbed-1` bundle and writes:

- `predictions.csv`
- `evidence/<row_id>.md`
- `usage.jsonl`

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

Default agent: `agents.telemetry_routed`.

It parses the window and failure count from each instruction, builds bounded candidates from metrics, logs, and traces, and emits a best guess even when telemetry or model calls are inconclusive. Evidence files include the selected answer, confidence, telemetry facts used, and nearby candidates ruled out.

## AI Tool Disclosure

Codex was used to generate the submission structure, Dockerfile, `run.py`, telemetry agent, validation helper, and draft documentation. The team should update this section before submission with every AI model, coding assistant, and agent framework used during final development, plus what was AI-generated versus manually written.

## Docs

- `REPORT.md`
- `eval/README.md`
- `docs/mantisgrid-track1-rca-por.md`
- `docs/mantisgrid-hackathon-implementation-plan.md`
- `docs/mantisgrid-codex-hackathon-guidelines.md`
