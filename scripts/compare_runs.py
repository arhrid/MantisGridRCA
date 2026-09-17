#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
from datetime import datetime
from pathlib import Path

PRICES = {
    "zai-org/GLM-4.7-Flash": (0.065, 0.40),
    "zai-org/GLM-5.3-Flash": (0.15, 0.50),
    "zai-org/GLM-4.6": (0.55, 2.20),
    "zai-org/GLM-4.7": (0.55, 2.20),
    "zai-org/GLM-5": (0.95, 3.15),
    "zai-org/GLM-5.1": (1.30, 4.30),
    "zai-org/GLM-5.2": (1.40, 4.40),
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def prediction_objects(prediction: str) -> list[dict]:
    pattern = (
        r'{\s*'
        r'(?:"root cause occurrence datetime":\s*"(.*?)")?,?\s*'
        r'(?:"root cause component":\s*"(.*?)")?,?\s*'
        r'(?:"root cause reason":\s*"(.*?)")?\s*}'
    )
    return [
        {
            "root cause occurrence datetime": d,
            "root cause component": c,
            "root cause reason": r,
        }
        for d, c, r in re.findall(pattern, str(prediction))
    ]


def expected_parts(scoring_points: str) -> tuple[list[str], list[str], list[str]]:
    components = re.findall(
        r"The (?:\d+-th|only) predicted root cause component is ([^\n]+)",
        scoring_points,
    )
    reasons = re.findall(
        r"The (?:\d+-th|only) predicted root cause reason is ([^\n]+)",
        scoring_points,
    )
    times = re.findall(
        r"The (?:\d+-th|only) root cause occurrence time is within 1 minutes "
        r"\(i.e., <=1min\) of ([^\n]+)",
        scoring_points,
    )
    return components, reasons, times


def close_enough(a: str, b: str) -> bool:
    try:
        t1 = datetime.strptime(a, "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(b, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return abs((t1 - t2).total_seconds()) <= 60


def evaluate(prediction: str, scoring_points: str) -> float:
    predicted = prediction_objects(prediction)
    components, reasons, times = expected_parts(scoring_points)
    expected_len = max(len(components), len(reasons), len(times))
    total = len(components) + len(reasons) + len(times)
    if not total:
        return 0.0

    best = -1
    if expected_len == len(predicted):
        for perm in itertools.permutations(predicted):
            cur = 0
            for i in range(expected_len):
                if len(components) == expected_len and perm[i]["root cause component"] == components[i]:
                    cur += 1
                if len(reasons) == expected_len and perm[i]["root cause reason"] == reasons[i]:
                    cur += 1
                if len(times) == expected_len and close_enough(times[i], perm[i]["root cause occurrence datetime"]):
                    cur += 1
            best = max(best, cur)
    return round(max(best, 0) / total, 2)


def run_cost(path: Path) -> tuple[float, dict[str, float]]:
    usage_path = path / "usage.jsonl"
    if not usage_path.exists():
        return 0.0, {}
    total = 0.0
    by_model: dict[str, float] = {}
    for line in usage_path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        for model, usage in rec.get("models", {}).items():
            pin, pout = PRICES.get(model, (0.0, 0.0))
            cost = (
                usage.get("prompt_tokens", 0) * pin / 1_000_000
                + usage.get("completion_tokens", 0) * pout / 1_000_000
            )
            by_model[model] = by_model.get(model, 0.0) + cost
            total += cost
    return total, by_model


def summarize(out: Path, queries: dict[str, dict]) -> dict:
    predictions = read_csv(out / "predictions.csv")
    scores = []
    missing_evidence = 0
    wall = 0.0
    prompt = 0
    completion = 0
    for row in predictions:
        query = queries.get(row["row_id"], {})
        scores.append(evaluate(row.get("prediction", ""), query.get("scoring_points", "")))
        if not (out / "evidence" / f"{row['row_id']}.md").exists():
            missing_evidence += 1
        wall += float(row.get("wall_s") or 0)
        prompt += int(float(row.get("prompt_tokens") or 0))
        completion += int(float(row.get("completion_tokens") or 0))
    cost, by_model = run_cost(out)
    cases = len(predictions)
    return {
        "out": str(out),
        "cases": cases,
        "mean_score": sum(scores) / cases if cases else 0.0,
        "fully_solved": sum(1 for score in scores if score == 1.0),
        "missing_evidence": missing_evidence,
        "wall_s": wall,
        "wall_s_per_case": wall / cases if cases else 0.0,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cost": cost,
        "cost_per_case": cost / cases if cases else 0.0,
        "cost_by_model": by_model,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True)
    parser.add_argument("--out", nargs="+", required=True)
    parser.add_argument("--report", default="")
    args = parser.parse_args()

    queries = {row["row_id"]: row for row in read_csv(Path(args.queries))}
    summaries = [summarize(Path(path), queries) for path in args.out]

    lines = [
        "# RCA Run Comparison",
        "",
        "| out | cases | mean score | solved | missing evidence | wall/case | cost/case | tokens/case |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        tokens_per_case = (
            (row["prompt_tokens"] + row["completion_tokens"]) / row["cases"]
            if row["cases"]
            else 0.0
        )
        lines.append(
            f"| `{row['out']}` | {row['cases']} | {row['mean_score']:.3f} | "
            f"{row['fully_solved']} | {row['missing_evidence']} | "
            f"{row['wall_s_per_case']:.1f}s | ${row['cost_per_case']:.4f} | "
            f"{tokens_per_case:,.0f} |"
        )
    lines += ["", "## Model Cost", ""]
    for row in summaries:
        lines.append(f"- `{row['out']}`: ${row['cost']:.4f} total")
        for model, cost in sorted(row["cost_by_model"].items()):
            lines.append(f"- `{model}`: ${cost:.4f}")

    text = "\n".join(lines) + "\n"
    print(text)
    if args.report:
        Path(args.report).write_text(text)


if __name__ == "__main__":
    main()
