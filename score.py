#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", str(text), re.S)
    return json.loads(m.group(0)) if m else {}


def normalize_answer(obj: dict) -> list[tuple[str, str, str]]:
    out = []
    for key in sorted(obj, key=lambda x: int(x) if str(x).isdigit() else str(x)):
        item = obj[key]
        out.append((
            str(item.get("root cause occurrence datetime", "")),
            str(item.get("root cause component", "")),
            str(item.get("root cause reason", "")),
        ))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--predictions", required=True)
    p.add_argument("--queries", required=True)
    args = p.parse_args()

    preds = pd.read_csv(args.predictions)
    queries = pd.read_csv(args.queries)
    if "scoring_points" not in queries.columns:
        print("queries file has no scoring_points column; shape-only score")
        print(f"predictions: {len(preds)} rows")
        return

    pred_by_id = {int(r.row_id): r.prediction for r in preds.itertuples(index=False)}
    strict = 0
    partial = 0
    total = 0
    for r in queries.itertuples(index=False):
        rid = int(r.row_id)
        if rid not in pred_by_id:
            continue
        total += 1
        try:
            pred = normalize_answer(extract_json(pred_by_id[rid]))
            gold = normalize_answer(extract_json(r.scoring_points))
        except Exception:
            continue
        if pred == gold:
            strict += 1
            partial += 1
            continue
        pred_text = " ".join(" ".join(x) for x in pred)
        gold_bits = [bit for triple in gold for bit in triple if bit]
        if gold_bits and any(bit in pred_text for bit in gold_bits):
            partial += 1

    denom = max(total, 1)
    print(f"cases scored: {total}")
    print(f"strict:  {strict}/{denom} = {strict / denom:.3f}")
    print(f"partial: {partial}/{denom} = {partial / denom:.3f}")


if __name__ == "__main__":
    main()
