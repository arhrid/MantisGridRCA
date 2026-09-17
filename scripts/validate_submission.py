#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

EVIDENCE_SECTIONS = ("Answer", "Confidence", "Evidence", "Ruled out")


def wanted_count(instruction: str) -> int:
    t = instruction.lower()
    for word, n in (("one failure", 1), ("a single failure", 1), ("two failures", 2),
                    ("three failures", 3), ("four failures", 4)):
        if word in t:
            return n
    return 1


def parse_prediction(text: str) -> dict:
    m = re.search(r"\{.*\}", str(text), re.S)
    if not m:
        raise ValueError("prediction has no JSON object")
    return json.loads(m.group(0))


def validate_evidence(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing {path.name}"]
    text = path.read_text()
    found = re.findall(r"^##\s+(.+?)\s*$", text, flags=re.M)
    errors = []
    for section in EVIDENCE_SECTIONS:
        if section not in found:
            errors.append(f"{path.name}: missing ## {section}")
    extras = [section for section in found if section not in EVIDENCE_SECTIONS]
    if extras:
        errors.append(f"{path.name}: unexpected top-level section(s): {', '.join(extras)}")
    return errors


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()
    out = Path(args.out)
    queries = pd.read_csv(args.queries)
    if args.limit:
        queries = queries.head(args.limit)
    preds = pd.read_csv(out / "predictions.csv")
    by_id = {int(r.row_id): r.prediction for r in preds.itertuples(index=False)}
    errors = []
    for r in queries.itertuples(index=False):
        rid = int(r.row_id)
        if rid not in by_id:
            errors.append(f"missing prediction for row_id={rid}")
            continue
        evidence_errors = validate_evidence(out / "evidence" / f"{rid}.md")
        errors.extend(f"evidence/{err}" for err in evidence_errors)
        try:
            obj = parse_prediction(by_id[rid])
        except Exception as e:
            errors.append(f"row_id={rid}: {e}")
            continue
        if len(obj) != wanted_count(r.instruction):
            errors.append(f"row_id={rid}: wrong failure count {len(obj)}")
        compact = json.dumps(obj)
        if "root cause component" in compact and "root cause reason" in compact:
            if compact.find("root cause component") > compact.find("root cause reason"):
                errors.append(f"row_id={rid}: component/reason key order invalid")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"validated {len(queries)} case(s) in {out}")


if __name__ == "__main__":
    main()
