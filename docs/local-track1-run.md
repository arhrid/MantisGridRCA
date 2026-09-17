# Local Track 1 Run Notes

Use the local virtual environment in this repo with the official Track 1 starter and data.

The Featherless key should only be exported in your shell or stored in a local ignored env file. Do not commit it.

```bash
cd /Users/benchong/Work/Hackathon/MantisGridRCA
export FEATHERLESS_API_KEY='...'
```

Alternatively create `/Users/benchong/Work/Hackathon/MantisGridRCA/.env.local`:

```bash
FEATHERLESS_API_KEY='...'
# Optional; omit unless instructed otherwise.
# FEATHERLESS_BASE_URL='https://api.featherless.ai/v1'
```

`.env.local` is ignored by git. The local run script loads it automatically when present.

Run the free heuristic baseline on two cases:

```bash
LIMIT=2 scripts/run_official_local.sh
```

Run the routed GLM starter on two cases:

```bash
LIMIT=2 AGENT=agents.routed scripts/run_official_local.sh
```

Run all 70 dev cases:

```bash
scripts/run_official_local.sh
```

Score the latest local-dev run:

```bash
.venv/bin/python \
  /Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/starter/score.py \
  --predictions /Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/out/local-dev/predictions.csv \
  --queries /Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/data/Market-cloudbed-1/dev/query_dev.csv
```

Notes:

- `query.csv` is the answer-free input shape.
- `dev/query_dev.csv` is the same 70 cases plus `scoring_points` for local scoring.
- The judged interface remains `python run.py --dataset /data --queries /data/query.csv --out /out`; the script above just maps those paths to local files.
- For Track 1, the required outputs are `predictions.csv`, `evidence/<row_id>.md`, and `usage.jsonl`.
