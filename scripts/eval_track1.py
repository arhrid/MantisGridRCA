#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
from datetime import datetime
from pathlib import Path

LEGAL_REASONS = {
    "container CPU load",
    "container memory load",
    "container network latency",
    "container network packet corruption",
    "container network packet retransmission",
    "container packet loss",
    "container process termination",
    "container read I/O load",
    "container write I/O load",
    "node CPU load",
    "node CPU spike",
    "node disk read I/O consumption",
    "node disk space consumption",
    "node disk write I/O consumption",
    "node memory consumption",
}


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


def classify(row_id: str, prediction: str, scoring_points: str, evidence: str) -> str:
    predicted = prediction_objects(prediction)
    components, reasons, times = expected_parts(scoring_points)
    expected_len = max(len(components), len(reasons), len(times))
    if expected_len != len(predicted):
        return "count_or_format_wrong"
    if any(p.get("root cause reason") and p["root cause reason"] not in LEGAL_REASONS for p in predicted):
        return "count_or_format_wrong"
    if "LLM decision failed" in evidence or "FEATHERLESS_API_KEY is not set" in evidence:
        return "model_failure"

    predicted_components = {p["root cause component"] for p in predicted}
    predicted_reasons = {p["root cause reason"] for p in predicted}
    expected_components = set(components)
    expected_reasons = set(reasons)

    if expected_components and expected_components & predicted_components:
        if expected_reasons and not (expected_reasons & predicted_reasons):
            return "reason_wrong"
        if times:
            return "time_wrong"
        return "unknown"

    if expected_components:
        if any(component in evidence for component in expected_components):
            return "candidate_present_model_wrong"
        return "candidate_missing"
    if expected_reasons and not (expected_reasons & predicted_reasons):
        return "reason_wrong"
    if times:
        return "time_wrong"
    return "unknown"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--queries", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    predictions = read_csv(out / "predictions.csv")
    queries = {row["row_id"]: row for row in read_csv(Path(args.queries))}
    report_rows = []

    for pred in predictions:
        row_id = pred["row_id"]
        query = queries[row_id]
        evidence_path = out / "evidence" / f"{row_id}.md"
        evidence = evidence_path.read_text() if evidence_path.exists() else ""
        score = evaluate(pred["prediction"], query.get("scoring_points", ""))
        failure_class = "perfect" if score == 1.0 else classify(
            row_id,
            pred["prediction"],
            query.get("scoring_points", ""),
            evidence,
        )
        report_rows.append({
            "row_id": row_id,
            "task": query.get("task_index", pred.get("task_index", "")),
            "score": score,
            "failure_class": failure_class,
            "wall_s": float(pred.get("wall_s") or 0),
            "prompt_tokens": int(float(pred.get("prompt_tokens") or 0)),
            "completion_tokens": int(float(pred.get("completion_tokens") or 0)),
        })

    mean_score = sum(r["score"] for r in report_rows) / len(report_rows) if report_rows else 0
    full = sum(1 for r in report_rows if r["score"] == 1.0)
    classes: dict[str, int] = {}
    for row in report_rows:
        classes[row["failure_class"]] = classes.get(row["failure_class"], 0) + 1

    report = out / "eval_report.md"
    lines = [
        "# Track 1 Eval Report",
        "",
        f"out: `{out}`",
        f"cases: {len(report_rows)}",
        f"mean_score: {mean_score:.3f}",
        f"fully_solved: {full} / {len(report_rows)}",
        f"total_wall_s: {sum(r['wall_s'] for r in report_rows):.1f}",
        f"prompt_tokens: {sum(r['prompt_tokens'] for r in report_rows):,}",
        f"completion_tokens: {sum(r['completion_tokens'] for r in report_rows):,}",
        "",
        "## Failure Classes",
        "",
    ]
    for name, count in sorted(classes.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {name}: {count}")
    lines += ["", "## Cases", "", "| row_id | task | score | failure_class | wall_s |", "|---|---|---:|---|---:|"]
    for row in report_rows:
        lines.append(
            f"| {row['row_id']} | {row['task']} | {row['score']:.2f} | "
            f"{row['failure_class']} | {row['wall_s']:.1f} |"
        )
    report.write_text("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\nWrote {report}")


if __name__ == "__main__":
    main()
