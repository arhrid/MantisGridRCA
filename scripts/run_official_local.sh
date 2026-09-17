#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OFFICIAL="${OFFICIAL_TRACK1_DIR:-/Users/benchong/Work/Hackathon/hackathon-2026-official/track-1}"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
DATASET="${DATASET:-$OFFICIAL/data/Market-cloudbed-1}"
QUERIES="${QUERIES:-$DATASET/dev/query_dev.csv}"
OUT="${OUT:-$OFFICIAL/out/local-dev}"
AGENT="${AGENT:-agents.heuristic}"
LIMIT="${LIMIT:-0}"

args=(
  "$OFFICIAL/starter/run.py"
  --dataset "$DATASET"
  --queries "$QUERIES"
  --out "$OUT"
  --agent "$AGENT"
)

if [[ "$LIMIT" != "0" ]]; then
  args+=(--limit "$LIMIT")
fi

"$PYTHON" "${args[@]}"

PREDICTIONS="$OUT/predictions.csv" QUERIES="$QUERIES" "$PYTHON" - <<'PY'
import csv
import os
import textwrap

predictions = os.environ["PREDICTIONS"]
queries = os.environ["QUERIES"]

if not os.path.exists(predictions):
    raise SystemExit(f"\nNo predictions found at {predictions}")

with open(queries, newline="") as fh:
    query_rows = {row["row_id"]: row for row in csv.DictReader(fh)}

with open(predictions, newline="") as fh:
    pred_rows = list(csv.DictReader(fh))

has_scoring = any("scoring_points" in row for row in query_rows.values())

print("\n=== Local run comparison ===")
for row in pred_rows:
    row_id = row["row_id"]
    q = query_rows.get(row_id, {})
    print(f"\nrow_id={row_id} task={q.get('task_index', row.get('task_index', ''))}")
    print("prediction:")
    print(textwrap.indent(row.get("prediction", "").strip(), "  "))
    if has_scoring:
        print("scoring_points:")
        print(textwrap.indent(q.get("scoring_points", "").strip(), "  "))
PY
