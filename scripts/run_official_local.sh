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

exec "$PYTHON" "${args[@]}"

