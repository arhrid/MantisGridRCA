#!/usr/bin/env python3
"""Submission entry point for Track 1.

The judges run:
    python run.py --dataset /data --queries /data/query.csv --out /out
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass
class Solution:
    prediction: str
    evidence: str = ""
    usage: dict = field(default_factory=dict)


COUNTS = ("prompt_tokens", "completion_tokens", "calls")


def per_model(usage: dict) -> dict:
    if usage and all(isinstance(v, dict) for v in usage.values()):
        return usage
    return {"unknown": usage} if any(usage.get(k) for k in COUNTS) else {}


def format_prediction(answers: list[dict]) -> str:
    """Build evaluator-compatible output.

    The key order is load-bearing for the OpenRCA evaluator regex:
    datetime, then component, then reason.
    """
    out = {}
    for i, a in enumerate(answers, 1):
        item = {}
        if a.get("datetime"):
            item["root cause occurrence datetime"] = a["datetime"]
        if a.get("component"):
            item["root cause component"] = a["component"]
        if a.get("reason"):
            item["root cause reason"] = a["reason"]
        out[str(i)] = item
    return "```json\n" + json.dumps(out, indent=4) + "\n```"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", required=True, help="bundle dir, containing telemetry/")
    p.add_argument("--queries", required=True, help="query.csv")
    p.add_argument("--out", required=True)
    p.add_argument("--agent", default="agents.telemetry_routed")
    p.add_argument("--limit", type=int, default=0, help="first N cases only")
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()

    dataset = Path(args.dataset).resolve()
    out = Path(args.out).resolve()
    (out / "evidence").mkdir(parents=True, exist_ok=True)

    queries = pd.read_csv(args.queries)
    if args.limit:
        queries = queries.head(args.limit)

    pred_path = out / "predictions.csv"
    done: set[int] = set()
    rows: list[dict] = []
    if args.resume and pred_path.exists():
        prev = pd.read_csv(pred_path)
        rows = prev.to_dict("records")
        done = set(prev.row_id.astype(int))
        print(f"resuming: {len(done)} case(s) already done")

    agent = importlib.import_module(args.agent)
    ctx = {"dataset_dir": dataset, "out_dir": out}
    for r in queries.itertuples(index=False):
        rid = int(r.row_id)
        if rid in done:
            continue
        t0 = time.time()
        try:
            sol = agent.solve(r.instruction, dataset, ctx)
        except Exception:
            sol = Solution(
                prediction="",
                evidence="AGENT RAISED\n\n```\n" + traceback.format_exc() + "```",
            )
        wall = time.time() - t0
        (out / "evidence" / f"{rid}.md").write_text(sol.evidence or "_no evidence_\n")
        models = per_model(sol.usage or {})
        rec = {
            "row_id": rid,
            "prediction": sol.prediction,
            "task_index": getattr(r, "task_index", ""),
            "wall_s": round(wall, 2),
            **{k: sum(m.get(k, 0) for m in models.values()) for k in COUNTS},
        }
        rows.append(rec)
        with (out / "usage.jsonl").open("a") as fh:
            fh.write(json.dumps({k: v for k, v in rec.items() if k != "prediction"} | {"models": models}) + "\n")

        tmp = pred_path.with_suffix(".csv.tmp")
        pd.DataFrame(rows).sort_values("row_id").to_csv(tmp, index=False)
        os.replace(tmp, pred_path)
        preview = (sol.prediction or "")[:60].replace("\n", " ")
        print(f"  row {rid:>3}  {wall:6.1f}s  {rec['prompt_tokens']:>8,} tok  {preview}")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} case(s) -> {pred_path}")
    if "wall_s" in df and len(df):
        print(f"wall-clock: mean {df.wall_s.mean():.1f}s  max {df.wall_s.max():.1f}s  total {df.wall_s.sum()/60:.1f}min")


if __name__ == "__main__":
    main()
