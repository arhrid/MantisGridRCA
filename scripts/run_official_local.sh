#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env.local}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

OFFICIAL="${OFFICIAL_TRACK1_DIR:-/Users/benchong/Work/Hackathon/hackathon-2026-official/track-1}"
STARTER="${STARTER_DIR:-$ROOT/starter}"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
DATASET="${DATASET:-$OFFICIAL/data/Market-cloudbed-1}"
QUERIES="${QUERIES:-$DATASET/dev/query_dev.csv}"
OUT="${OUT:-$OFFICIAL/out/local-dev}"
AGENT="${AGENT:-agents.heuristic}"
LIMIT="${LIMIT:-0}"
RUN_NAME="${RUN_NAME:-$AGENT}"
CLEAN_OUT="${CLEAN_OUT:-1}"

args=(
  "$STARTER/run.py"
  --dataset "$DATASET"
  --queries "$QUERIES"
  --out "$OUT"
  --agent "$AGENT"
)

if [[ "$LIMIT" != "0" ]]; then
  args+=(--limit "$LIMIT")
fi

cat <<EOF
=== Track 1 local run ===
run:     $RUN_NAME
agent:   $AGENT
limit:   $LIMIT
queries: $QUERIES
out:     $OUT
EOF

if [[ "$CLEAN_OUT" != "0" ]]; then
  rm -rf "$OUT"
fi
mkdir -p "$OUT"

"$PYTHON" "${args[@]}"

PREDICTIONS="$OUT/predictions.csv" QUERIES="$QUERIES" RUN_NAME="$RUN_NAME" AGENT="$AGENT" OUT="$OUT" "$PYTHON" - <<'PY'
import csv
import itertools
import os
import re
import textwrap
from datetime import datetime

predictions = os.environ["PREDICTIONS"]
queries = os.environ["QUERIES"]
run_name = os.environ["RUN_NAME"]
agent = os.environ["AGENT"]
out = os.environ["OUT"]

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

def evaluate(prediction: str, scoring_points: str) -> float:
    predict_pattern = (
        r'{\s*'
        r'(?:"root cause occurrence datetime":\s*"(.*?)")?,?\s*'
        r'(?:"root cause component":\s*"(.*?)")?,?\s*'
        r'(?:"root cause reason":\s*"(.*?)")?\s*}'
    )
    predict_results = [
        {"root cause occurrence datetime": d, "root cause component": c,
         "root cause reason": r}
        for d, c, r in re.findall(predict_pattern, str(prediction))
    ]
    components = re.findall(
        r"The (?:\d+-th|only) predicted root cause component is ([^\n]+)", scoring_points)
    reasons = re.findall(
        r"The (?:\d+-th|only) predicted root cause reason is ([^\n]+)", scoring_points)
    times = re.findall(
        r"The (?:\d+-th|only) root cause occurrence time is within 1 minutes "
        r"\(i.e., <=1min\) of ([^\n]+)", scoring_points)
    expected_len = max(len(components), len(reasons), len(times))
    total = len(components) + len(reasons) + len(times)

    def close_enough(a: str, b: str) -> bool:
        try:
            t1 = datetime.strptime(a, "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(b, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False
        return abs((t1 - t2).total_seconds()) <= 60

    best = -1
    if expected_len == len(predict_results):
        for perm in itertools.permutations(predict_results):
            cur = 0
            for i in range(expected_len):
                if len(components) == expected_len and perm[i]["root cause component"] == components[i]:
                    cur += 1
                if len(reasons) == expected_len and perm[i]["root cause reason"] == reasons[i]:
                    cur += 1
                if len(times) == expected_len and close_enough(times[i], perm[i]["root cause occurrence datetime"]):
                    cur += 1
            best = max(best, cur)
    return round(max(best, 0) / total, 2) if total else 0.0

if has_scoring:
    scores = []
    by_task = {}
    for row in pred_rows:
        q = query_rows.get(row["row_id"], {})
        score = evaluate(row.get("prediction", ""), q.get("scoring_points", ""))
        scores.append(score)
        task = q.get("task_index", row.get("task_index", "?"))
        by_task.setdefault(task, []).append(score)

    mean_score = sum(scores) / len(scores) if scores else 0.0
    fully_solved = sum(1 for s in scores if s == 1.0)
    print("\n=== Local run score summary ===")
    print(f"run:          {run_name}")
    print(f"agent:        {agent}")
    print(f"cases:        {len(scores)}")
    print(f"mean score:   {mean_score:.3f}")
    print(f"fully solved: {fully_solved} / {len(scores)}")
    print(f"out:          {out}")
    for task in sorted(by_task):
        vals = by_task[task]
        print(f"{task}:       {len(vals)} case(s), mean {sum(vals)/len(vals):.3f}")
PY
